/**
 * Sağlayıcıdan bağımsız AI katmanı.
 *
 * Sağlayıcılar:
 *  - openai      → OpenAI API
 *  - gemini      → Google Gemini
 *  - openrouter  → OpenRouter
 *
 * Davranış:
 *  - AI_PROVIDER birincil sağlayıcıyı seçer ("auto" = varsayılan sıra).
 *  - Bir sağlayıcı hata verirse sıradakine geçilir.
 *  - Varsayılan sıra: openai → gemini → openrouter.
 *  - Anahtarı tanımlı olmayan sağlayıcı zincire girmez.
 *  - Hepsi düşerse AllProvidersFailed fırlatılır.
 *
 * Bu dosya Next.js API'lerine bağımlı değildir;
 * Node ile doğrudan test edilebilir.
 */

export type ProviderName =
  | "openai"
  | "gemini"
  | "openrouter";

/** Yedek zincirin varsayılan sırası. */
export const PROVIDER_ORDER: readonly ProviderName[] = [
  "openai",
  "gemini",
  "openrouter",
];

export type ProviderRequest = {
  /** Sağlayıcıya gönderilecek tam metin. */
  prompt: string;

  /** data:image/png;base64,... biçiminde görsel ya da ham base64. */
  imageData?: string | null;
};

export type ProviderResult = {
  provider: ProviderName;
  model: string;
  text: string;
};

export type Attempt = {
  provider: ProviderName;
  /** Upstream HTTP durumu; ağ hatasında null. */
  status: number | null;
  error: string;
};

export type Env = Record<string, string | undefined>;

const TEMPERATURE = 0.2;
const MAX_OUTPUT_TOKENS = 1200;
const DEFAULT_TIMEOUT_MS = 45_000;

/**
 * Tek sağlayıcının başarısızlığı.
 */
export class ProviderError extends Error {
  status: number;

  constructor(
    message: string,
    status: number,
  ) {
    super(message);
    this.name = "ProviderError";
    this.status = status;
  }
}

/** Zincirdeki tüm sağlayıcıların başarısızlığı. */
export class AllProvidersFailed extends Error {
  status = 502;
  attempts: Attempt[];

  constructor(attempts: Attempt[]) {
    super(
      `AI sağlayıcılarının tamamı başarısız oldu (` +
        attempts
          .map(
            (a) =>
              `${a.provider}: ${a.error}`,
          )
          .join(" | ") +
        ")",
    );

    this.name = "AllProvidersFailed";
    this.attempts = attempts;
  }
}

function isProviderName(
  value: string,
): value is ProviderName {
  return (
    value === "openai" ||
    value === "gemini" ||
    value === "openrouter"
  );
}

function timeoutMs(
  env: Env,
): number {
  const parsed = Number(
    env.AI_TIMEOUT_MS,
  );

  return Number.isFinite(parsed) &&
    parsed >= 1000
    ? parsed
    : DEFAULT_TIMEOUT_MS;
}

/** Sağlayıcının gerekli ayarları tanımlı mı? */
export function isConfigured(
  name: ProviderName,
  env: Env = process.env,
): boolean {
  if (name === "openai") {
    return Boolean(
      env.OPENAI_API_KEY?.trim(),
    );
  }

  if (name === "gemini") {
    return Boolean(
      env.GEMINI_API_KEY?.trim(),
    );
  }

  if (name === "openrouter") {
    return Boolean(
      env.OPENROUTER_API_KEY?.trim(),
    );
  }

  return false;
}

/**
 * Denenecek sağlayıcı sırası.
 *
 * AI_PROVIDER=auto:
 *   OpenAI → Gemini → OpenRouter
 *
 * OpenAI key yoksa:
 *   Gemini → OpenRouter
 *
 * AI_FALLBACK_ORDER verilirse o sıra kullanılır.
 */
export function resolveChain(
  env: Env = process.env,
): ProviderName[] {
  const explicit = (
    env.AI_FALLBACK_ORDER ?? ""
  )
    .split(",")
    .map((part) => part.trim())
    .filter(isProviderName);

  const base =
    explicit.length > 0
      ? explicit
      : [...PROVIDER_ORDER];

  const primary = (
    env.AI_PROVIDER ?? "auto"
  ).trim();

  const ordered = isProviderName(primary)
    ? [
        primary,
        ...base.filter(
          (p) => p !== primary,
        ),
      ]
    : base;

  return ordered.filter(
    (name) =>
      isConfigured(name, env),
  );
}

/** data:image/png;base64,... ayrıştırıcı. */
export function parseImageData(
  imageData: string,
): {
  mimeType: string;
  data: string;
} {
  const match =
    /^data:([^;,]+);base64,([\s\S]*)$/.exec(
      imageData,
    );

  if (match) {
    return {
      mimeType: match[1],
      data: match[2],
    };
  }

  return {
    mimeType: "image/jpeg",
    data: imageData,
  };
}

function extractErrorMessage(
  body: unknown,
  status: number,
): string {
  if (
    typeof body === "string" &&
    body.trim()
  ) {
    return body
      .trim()
      .slice(0, 300);
  }

  if (
    body &&
    typeof body === "object"
  ) {
    const record = body as {
      error?: unknown;
      message?: unknown;
    };

    const nested =
      record.error;

    if (
      typeof nested === "string" &&
      nested.trim()
    ) {
      return nested
        .trim()
        .slice(0, 300);
    }

    if (
      nested &&
      typeof nested === "object"
    ) {
      const message = (
        nested as {
          message?: unknown;
        }
      ).message;

      if (
        typeof message === "string" &&
        message.trim()
      ) {
        return message
          .trim()
          .slice(0, 300);
      }
    }

    if (
      typeof record.message ===
        "string" &&
      record.message.trim()
    ) {
      return record.message
        .trim()
        .slice(0, 300);
    }
  }

  return `HTTP ${status}`;
}

async function postJson(
  url: string,
  headers: Record<string, string>,
  payload: unknown,
  env: Env,
): Promise<unknown> {
  let response: Response;

  try {
    response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
      signal:
        AbortSignal.timeout(
          timeoutMs(env),
        ),
    });
  } catch (error) {
    const name =
      error instanceof Error
        ? error.name
        : "";

    const reason =
      name === "TimeoutError"
        ? "zaman aşımı"
        : name === "AbortError"
          ? "istek iptal edildi"
          : "bağlantı kurulamadı";

    throw new ProviderError(
      reason,
      0,
    );
  }

  const raw =
    await response.text();

  let body: unknown = null;

  if (raw) {
    try {
      body = JSON.parse(raw);
    } catch {
      body = raw;
    }
  }

  if (!response.ok) {
    throw new ProviderError(
      extractErrorMessage(
        body,
        response.status,
      ),
      response.status,
    );
  }

  return body;
}

/** OpenAI-compatible content dizisi. */
function openAiContent(
  request: ProviderRequest,
): unknown[] {
  const content: unknown[] = [
    {
      type: "text",
      text: request.prompt,
    },
  ];

  if (request.imageData) {
    const dataUrl =
      request.imageData.startsWith(
        "data:",
      )
        ? request.imageData
        : `data:${
            parseImageData(
              request.imageData,
            ).mimeType
          };base64,${request.imageData}`;

    content.push({
      type: "image_url",
      image_url: {
        url: dataUrl,
      },
    });
  }

  return content;
}

/** OpenAI-compatible chat completion parser. */
function readChatCompletion(
  body: unknown,
): string {
  const choices = (
    body as {
      choices?: {
        message?: {
          content?: unknown;
        };
      }[];
    } | null
  )?.choices;

  const content =
    choices?.[0]?.message
      ?.content;

  if (
    typeof content === "string" &&
    content.trim()
  ) {
    return content.trim();
  }

  if (Array.isArray(content)) {
    const joined =
      content
        .map((part) =>
          part &&
          typeof part ===
            "object"
            ? String(
                (
                  part as {
                    text?: unknown;
                  }
                ).text ?? "",
              )
            : "",
        )
        .join("")
        .trim();

    if (joined) {
      return joined;
    }
  }

  return "";
}

/* ============================================================
 * OPENAI
 * ============================================================ */

let cachedOpenAIModel:
  | string
  | null = null;

function openAIBaseUrl(
  env: Env,
): string {
  return (
    env.OPENAI_BASE_URL?.trim() ||
    "https://api.openai.com/v1"
  ).replace(/\/+$/, "");
}

function openAIModelPriority(
  model: string,
): number {
  const value =
    model.toLowerCase();

  if (
    value.includes("5.6") ||
    value.includes("5-6")
  ) {
    return 100;
  }

  if (value.includes("5")) {
    return 90;
  }

  if (value.includes("4.1")) {
    return 80;
  }

  if (value.includes("4o")) {
    return 70;
  }

  if (value.includes("o4")) {
    return 60;
  }

  if (value.includes("o3")) {
    return 50;
  }

  return 10;
}

function isUsableOpenAIModel(
  model: string,
): boolean {
  const value =
    model.toLowerCase();

  const blocked = [
    "embedding",
    "moderation",
    "tts",
    "whisper",
    "transcribe",
    "search",
    "image",
    "audio",
    "realtime",
    "dall-e",
  ];

  if (
    blocked.some((item) =>
      value.includes(item),
    )
  ) {
    return false;
  }

  return (
    value.startsWith("gpt-") ||
    value.startsWith("o")
  );
}

/**
 * OPENAI_MODEL verilmişse onu kullanır.
 *
 * Boş bırakılmışsa /models üzerinden
 * erişilebilir modelleri keşfetmeye çalışır.
 */
async function discoverOpenAIModel(
  env: Env,
): Promise<string> {
  const forced =
    env.OPENAI_MODEL?.trim();

  if (forced) {
    return forced;
  }

  if (cachedOpenAIModel) {
    return cachedOpenAIModel;
  }

  const apiKey =
    env.OPENAI_API_KEY?.trim();

  if (!apiKey) {
    throw new ProviderError(
      "OPENAI_API_KEY tanımlı değil",
      500,
    );
  }

  let response: Response;

  try {
    response = await fetch(
      `${openAIBaseUrl(env)}/models`,
      {
        method: "GET",
        headers: {
          authorization:
            `Bearer ${apiKey}`,
        },
        signal:
          AbortSignal.timeout(
            timeoutMs(env),
          ),
      },
    );
  } catch {
    throw new ProviderError(
      "OpenAI model listesine bağlantı kurulamadı",
      0,
    );
  }

  const raw =
    await response.text();

  let body: unknown = null;

  try {
    body = raw
      ? JSON.parse(raw)
      : null;
  } catch {
    body = raw;
  }

  if (!response.ok) {
    throw new ProviderError(
      "OpenAI model listesi alınamadı",
      response.status,
    );
  }

  const models =
    (
      body as {
        data?: {
          id?: unknown;
        }[];
      } | null
    )?.data ?? [];

  const usable =
    models
      .map((item) =>
        typeof item.id ===
          "string"
          ? item.id
          : "",
      )
      .filter(
        isUsableOpenAIModel,
      )
      .sort(
        (a, b) =>
          openAIModelPriority(b) -
          openAIModelPriority(a),
      );

  if (usable.length === 0) {
    throw new ProviderError(
      "OpenAI hesabında kullanılabilir metin modeli bulunamadı",
      500,
    );
  }

  cachedOpenAIModel =
    usable[0];

  return cachedOpenAIModel;
}

async function callOpenAI(
  request: ProviderRequest,
  env: Env,
): Promise<ProviderResult> {
  const apiKey =
    env.OPENAI_API_KEY?.trim();

  if (!apiKey) {
    throw new ProviderError(
      "OPENAI_API_KEY tanımlı değil",
      500,
    );
  }

  const model =
    await discoverOpenAIModel(
      env,
    );

  const body =
    await postJson(
      `${openAIBaseUrl(env)}/chat/completions`,
      {
        "content-type":
          "application/json",
        authorization:
          `Bearer ${apiKey}`,
      },
      {
        model,
        messages: [
          {
            role: "user",
            content:
              openAiContent(
                request,
              ),
          },
        ],
        temperature:
          TEMPERATURE,
        max_tokens:
          MAX_OUTPUT_TOKENS,
      },
      env,
    );

  const text =
    readChatCompletion(body);

  if (!text) {
    throw new ProviderError(
      "OpenAI boş yanıt döndürdü",
      502,
    );
  }

  return {
    provider: "openai",
    model,
    text,
  };
}

/* ============================================================
 * GEMINI
 * ============================================================ */

async function callGemini(
  request: ProviderRequest,
  env: Env,
): Promise<ProviderResult> {
  const apiKey =
    env.GEMINI_API_KEY?.trim();

  if (!apiKey) {
    throw new ProviderError(
      "GEMINI_API_KEY tanımlı değil",
      500,
    );
  }

  const model =
    env.GEMINI_MODEL?.trim() ||
    "gemini-flash-latest";

  const baseUrl = (
    env.GEMINI_BASE_URL?.trim() ||
    "https://generativelanguage.googleapis.com"
  ).replace(/\/+$/, "");

  const parts: Record<
    string,
    unknown
  >[] = [
    {
      text: request.prompt,
    },
  ];

  if (request.imageData) {
    const image =
      parseImageData(
        request.imageData,
      );

    parts.push({
      inline_data: {
        mime_type:
          image.mimeType,
        data: image.data,
      },
    });
  }

  const body =
    await postJson(
      `${baseUrl}/v1beta/models/${encodeURIComponent(
        model,
      )}:generateContent`,
      {
        "content-type":
          "application/json",
        "x-goog-api-key":
          apiKey,
      },
      {
        contents: [
          {
            role: "user",
            parts,
          },
        ],
        generationConfig: {
          temperature:
            TEMPERATURE,
          maxOutputTokens:
            MAX_OUTPUT_TOKENS,
        },
      },
      env,
    );

  const parsed =
    body as {
      candidates?: {
        content?: {
          parts?: {
            text?: string;
          }[];
        };
      }[];
      promptFeedback?: {
        blockReason?: string;
      };
    } | null;

  const text = (
    parsed
      ?.candidates?.[0]
      ?.content?.parts ?? []
  )
    .map(
      (part) =>
        part.text ?? "",
    )
    .join("")
    .trim();

  if (!text) {
    const blockReason =
      parsed
        ?.promptFeedback
        ?.blockReason;

    throw new ProviderError(
      blockReason
        ? `Gemini içeriği engelledi (${blockReason})`
        : "Gemini boş yanıt döndürdü",
      502,
    );
  }

  return {
    provider: "gemini",
    model,
    text,
  };
}

/* ============================================================
 * OPENROUTER
 * ============================================================ */

async function callOpenRouter(
  request: ProviderRequest,
  env: Env,
): Promise<ProviderResult> {
  const apiKey =
    env.OPENROUTER_API_KEY?.trim();

  if (!apiKey) {
    throw new ProviderError(
      "OPENROUTER_API_KEY tanımlı değil",
      500,
    );
  }

  const model =
    env.OPENROUTER_MODEL?.trim() ||
    "openrouter/free";

  const baseUrl = (
    env.OPENROUTER_BASE_URL?.trim() ||
    "https://openrouter.ai/api/v1"
  ).replace(/\/+$/, "");

  const body =
    await postJson(
      `${baseUrl}/chat/completions`,
      {
        "content-type":
          "application/json",
        authorization:
          `Bearer ${apiKey}`,
        "HTTP-Referer":
          env.AI_APP_URL?.trim() ||
          "http://localhost:3000",
        "X-Title":
          "LGS AI Coach",
      },
      {
        model,
        messages: [
          {
            role: "user",
            content:
              openAiContent(
                request,
              ),
          },
        ],
        temperature:
          TEMPERATURE,
        max_tokens:
          MAX_OUTPUT_TOKENS,
      },
      env,
    );

  const text =
    readChatCompletion(body);

  if (!text) {
    throw new ProviderError(
      "OpenRouter boş yanıt döndürdü",
      502,
    );
  }

  return {
    provider: "openrouter",
    model,
    text,
  };
}

/* ============================================================
 * PROVIDER DISPATCH
 * ============================================================ */

function callProvider(
  name: ProviderName,
  request: ProviderRequest,
  env: Env,
): Promise<ProviderResult> {
  if (name === "openai") {
    return callOpenAI(
      request,
      env,
    );
  }

  if (name === "gemini") {
    return callGemini(
      request,
      env,
    );
  }

  return callOpenRouter(
    request,
    env,
  );
}

/* ============================================================
 * AI RUNNER
 * ============================================================ */

export async function runAI(
  request: ProviderRequest,
  env: Env = process.env,
): Promise<ProviderResult> {
  const chain =
    resolveChain(env);

  if (chain.length === 0) {
    throw new ProviderError(
      "Hiçbir AI sağlayıcısı yapılandırılmamış. " +
        ".env.local dosyasına " +
        "OPENAI_API_KEY, " +
        "GEMINI_API_KEY veya " +
        "OPENROUTER_API_KEY değerlerinden " +
        "birini ekleyin.",
      500,
    );
  }

  const attempts: Attempt[] = [];

  for (
    const provider of chain
  ) {
    try {
      return await callProvider(
        provider,
        request,
        env,
      );
    } catch (error) {
      const failure =
        error instanceof
        ProviderError
          ? error
          : new ProviderError(
              error instanceof
                Error
                ? error.message
                : "Bilinmeyen hata",
              0,
            );

      attempts.push({
        provider,
        status:
          failure.status ||
          null,
        error:
          failure.message,
      });
    }
  }

  throw new AllProvidersFailed(
    attempts,
  );
}
