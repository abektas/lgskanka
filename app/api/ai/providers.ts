/**
 * Sağlayıcıdan bağımsız AI katmanı.
 *
 *  - gemini      → Google Gemini          (GEMINI_API_KEY,  GEMINI_MODEL)
 *  - openrouter  → OpenRouter             (OPENROUTER_API_KEY, OPENROUTER_MODEL)
 *  - local       → OpenAI-uyumlu yerel sunucu: LM Studio / Ollama / vLLM
 *                                          (LOCAL_AI_BASE_URL, LOCAL_AI_MODEL, LOCAL_AI_API_KEY)
 *
 * Davranış:
 *  - `AI_PROVIDER` birincil sağlayıcıyı seçer ("auto" = varsayılan sıra).
 *  - Bir sağlayıcı hata verirse sıradakine geçilir (varsayılan sıra: gemini → openrouter → local).
 *  - Anahtarı/URL'i tanımlı olmayan sağlayıcı zincire hiç girmez.
 *  - Hepsi düşerse `AllProvidersFailed` fırlatılır; her denemenin sebebi hata içinde taşınır.
 *
 * Bu dosya Next.js API'lerine bağımlı değildir; Node ile doğrudan test edilebilir.
 */

export type ProviderName = "gemini" | "openrouter" | "local";

/** Yedek zincirin varsayılan sırası. */
export const PROVIDER_ORDER: readonly ProviderName[] = ["gemini", "openrouter", "local"];

export type ProviderRequest = {
  /** Sağlayıcıya gönderilecek tam metin (sistem şablonu + öğrenci bilgileri). */
  prompt: string;
  /** `data:image/png;base64,...` biçiminde görsel ya da ham base64. Opsiyonel. */
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
 * (Alanlar bilinçli olarak parametre özelliği değil: bu dosya Node'un düz TypeScript
 * çalıştırmasıyla da import edilebilsin diye — bkz. scripts/ai-providers.smoke.mjs.)
 */
export class ProviderError extends Error {
  status: number;

  constructor(message: string, status: number) {
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
        attempts.map((a) => `${a.provider}: ${a.error}`).join(" | ") +
        ")",
    );
    this.name = "AllProvidersFailed";
    this.attempts = attempts;
  }
}

function isProviderName(value: string): value is ProviderName {
  return value === "gemini" || value === "openrouter" || value === "local";
}

function timeoutMs(env: Env): number {
  const parsed = Number(env.AI_TIMEOUT_MS);
  return Number.isFinite(parsed) && parsed >= 1000 ? parsed : DEFAULT_TIMEOUT_MS;
}

/** Sağlayıcının gerekli ayarları tanımlı mı? */
export function isConfigured(name: ProviderName, env: Env = process.env): boolean {
  if (name === "gemini") return Boolean(env.GEMINI_API_KEY?.trim());
  if (name === "openrouter") return Boolean(env.OPENROUTER_API_KEY?.trim());
  return Boolean(env.LOCAL_AI_BASE_URL?.trim());
}

/**
 * Denenecek sağlayıcı sırası.
 * `AI_PROVIDER` verilen sağlayıcıyı başa alır; kalanlar varsayılan sırayı korur.
 * `AI_FALLBACK_ORDER=openrouter,local` ile sıra tamamen değiştirilebilir.
 */
export function resolveChain(env: Env = process.env): ProviderName[] {
  const explicit = (env.AI_FALLBACK_ORDER ?? "")
    .split(",")
    .map((part) => part.trim())
    .filter(isProviderName);
  const base = explicit.length > 0 ? explicit : [...PROVIDER_ORDER];

  const primary = (env.AI_PROVIDER ?? "auto").trim();
  const ordered = isProviderName(primary) ? [primary, ...base.filter((p) => p !== primary)] : base;

  return ordered.filter((name) => isConfigured(name, env));
}

/** `data:image/png;base64,...` ayrıştırıcı; ham base64 gelirse image/jpeg varsayar. */
export function parseImageData(imageData: string): { mimeType: string; data: string } {
  const match = /^data:([^;,]+);base64,([\s\S]*)$/.exec(imageData);
  if (match) return { mimeType: match[1], data: match[2] };
  return { mimeType: "image/jpeg", data: imageData };
}

function extractErrorMessage(body: unknown, status: number): string {
  if (typeof body === "string" && body.trim()) return body.trim().slice(0, 300);
  if (body && typeof body === "object") {
    const record = body as { error?: unknown; message?: unknown };
    const nested = record.error;
    if (typeof nested === "string" && nested.trim()) return nested.trim().slice(0, 300);
    if (nested && typeof nested === "object") {
      const message = (nested as { message?: unknown }).message;
      if (typeof message === "string" && message.trim()) return message.trim().slice(0, 300);
    }
    if (typeof record.message === "string" && record.message.trim()) {
      return record.message.trim().slice(0, 300);
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
      signal: AbortSignal.timeout(timeoutMs(env)),
    });
  } catch (error) {
    const name = error instanceof Error ? error.name : "";
    const reason =
      name === "TimeoutError" ? "zaman aşımı" : name === "AbortError" ? "istek iptal edildi" : "bağlantı kurulamadı";
    throw new ProviderError(`${reason} (${url})`, 0);
  }

  const raw = await response.text();
  let body: unknown = null;
  if (raw) {
    try {
      body = JSON.parse(raw);
    } catch {
      body = raw;
    }
  }

  if (!response.ok) throw new ProviderError(extractErrorMessage(body, response.status), response.status);
  return body;
}

/** OpenAI uyumlu `content` dizisi (metin + opsiyonel görsel). */
function openAiContent(request: ProviderRequest): unknown[] {
  const content: unknown[] = [{ type: "text", text: request.prompt }];
  if (request.imageData) {
    const dataUrl = request.imageData.startsWith("data:")
      ? request.imageData
      : `data:${parseImageData(request.imageData).mimeType};base64,${request.imageData}`;
    content.push({ type: "image_url", image_url: { url: dataUrl } });
  }
  return content;
}

function readChatCompletion(body: unknown): string {
  const choices = (body as { choices?: { message?: { content?: unknown } }[] } | null)?.choices;
  const content = choices?.[0]?.message?.content;
  if (typeof content === "string" && content.trim()) return content.trim();
  if (Array.isArray(content)) {
    const joined = content
      .map((part) => (part && typeof part === "object" ? String((part as { text?: unknown }).text ?? "") : ""))
      .join("")
      .trim();
    if (joined) return joined;
  }
  return "";
}

async function callGemini(request: ProviderRequest, env: Env): Promise<ProviderResult> {
  const apiKey = env.GEMINI_API_KEY?.trim();
  if (!apiKey) throw new ProviderError("GEMINI_API_KEY tanımlı değil", 500);

  const model = env.GEMINI_MODEL?.trim() || "gemini-flash-latest";
  const baseUrl = (env.GEMINI_BASE_URL?.trim() || "https://generativelanguage.googleapis.com").replace(/\/+$/, "");

  const parts: Record<string, unknown>[] = [{ text: request.prompt }];
  if (request.imageData) {
    const image = parseImageData(request.imageData);
    parts.push({ inline_data: { mime_type: image.mimeType, data: image.data } });
  }

  const body = await postJson(
    `${baseUrl}/v1beta/models/${model}:generateContent`,
    { "content-type": "application/json", "x-goog-api-key": apiKey },
    {
      contents: [{ role: "user", parts }],
      generationConfig: { temperature: TEMPERATURE, maxOutputTokens: MAX_OUTPUT_TOKENS },
    },
    env,
  );

  const parsed = body as {
    candidates?: { content?: { parts?: { text?: string }[] } }[];
    promptFeedback?: { blockReason?: string };
  } | null;

  const text = (parsed?.candidates?.[0]?.content?.parts ?? [])
    .map((part) => part.text ?? "")
    .join("")
    .trim();

  if (!text) {
    const blockReason = parsed?.promptFeedback?.blockReason;
    throw new ProviderError(
      blockReason ? `Gemini içeriği engelledi (${blockReason})` : "Gemini boş yanıt döndürdü",
      502,
    );
  }

  return { provider: "gemini", model, text };
}

async function callOpenRouter(request: ProviderRequest, env: Env): Promise<ProviderResult> {
  const apiKey = env.OPENROUTER_API_KEY?.trim();
  if (!apiKey) throw new ProviderError("OPENROUTER_API_KEY tanımlı değil", 500);

  const model = env.OPENROUTER_MODEL?.trim() || "openrouter/free";
  const baseUrl = (env.OPENROUTER_BASE_URL?.trim() || "https://openrouter.ai/api/v1").replace(/\/+$/, "");

  const body = await postJson(
    `${baseUrl}/chat/completions`,
    {
      "content-type": "application/json",
      authorization: `Bearer ${apiKey}`,
      // HTTP başlıkları yalnızca latin-1 kabul eder → başlıkta Türkçe karakter KULLANMA.
      "HTTP-Referer": env.AI_APP_URL?.trim() || "http://localhost:3000",
      "X-Title": "LGS AI Coach",
    },
    {
      model,
      messages: [{ role: "user", content: openAiContent(request) }],
      temperature: TEMPERATURE,
      max_tokens: MAX_OUTPUT_TOKENS,
    },
    env,
  );

  const text = readChatCompletion(body);
  if (!text) throw new ProviderError("OpenRouter boş yanıt döndürdü", 502);

  return { provider: "openrouter", model, text };
}

async function callLocal(request: ProviderRequest, env: Env): Promise<ProviderResult> {
  const baseUrl = env.LOCAL_AI_BASE_URL?.trim();
  if (!baseUrl) throw new ProviderError("LOCAL_AI_BASE_URL tanımlı değil", 500);

  const model = env.LOCAL_AI_MODEL?.trim() || "local-model";
  const headers: Record<string, string> = { "content-type": "application/json" };
  const localKey = env.LOCAL_AI_API_KEY?.trim();
  if (localKey) headers.authorization = `Bearer ${localKey}`;

  const body = await postJson(
    `${baseUrl.replace(/\/+$/, "")}/chat/completions`,
    headers,
    {
      model,
      messages: [{ role: "user", content: openAiContent(request) }],
      temperature: TEMPERATURE,
      max_tokens: MAX_OUTPUT_TOKENS,
    },
    env,
  );

  const text = readChatCompletion(body);
  if (!text) throw new ProviderError("Yerel model boş yanıt döndürdü", 502);

  return { provider: "local", model, text };
}

function callProvider(name: ProviderName, request: ProviderRequest, env: Env): Promise<ProviderResult> {
  if (name === "gemini") return callGemini(request, env);
  if (name === "openrouter") return callOpenRouter(request, env);
  return callLocal(request, env);
}

/**
 * İsteği sırayla sağlayıcılara dener, ilk başarılı yanıtı döner.
 * Hiçbiri çalışmazsa `AllProvidersFailed`, hiç sağlayıcı yoksa `ProviderError(500)` fırlatır.
 */
export async function runAI(request: ProviderRequest, env: Env = process.env): Promise<ProviderResult> {
  const chain = resolveChain(env);

  if (chain.length === 0) {
    throw new ProviderError(
      "Hiçbir AI sağlayıcısı yapılandırılmamış. .env.local dosyasına GEMINI_API_KEY, " +
        "OPENROUTER_API_KEY veya LOCAL_AI_BASE_URL değerlerinden birini ekleyin.",
      500,
    );
  }

  const attempts: Attempt[] = [];

  for (const provider of chain) {
    try {
      return await callProvider(provider, request, env);
    } catch (error) {
      const failure =
        error instanceof ProviderError
          ? error
          : new ProviderError(error instanceof Error ? error.message : "Bilinmeyen hata", 0);
      attempts.push({ provider, status: failure.status || null, error: failure.message });
    }
  }

  throw new AllProvidersFailed(attempts);
}
