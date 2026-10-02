/**
 * LGS AI Coach — AI Provider Smoke Tests
 *
 * Mimari:
 *   OpenAI -> Gemini -> OpenRouter
 *
 * Gerçek API çağrısı yapmaz.
 * Tüm provider'lar lokal stub sunucuları ile test edilir.
 */

import assert from "node:assert/strict";
import http from "node:http";

import {
  AllProvidersFailed,
  ProviderError,
  resolveChain,
  runAI,
} from "../app/api/ai/providers.ts";


/* ============================================================
 * TEST SERVER
 * ============================================================ */

function startStub(respond) {
  const received = [];

  const server = http.createServer((req, res) => {
    let raw = "";

    req.on("data", (chunk) => {
      raw += chunk;
    });

    req.on("end", () => {
      let body = null;

      try {
        body = JSON.parse(raw);
      } catch {
        // boş veya JSON olmayan body
      }

      received.push({
        url: req.url,
        method: req.method,
        headers: req.headers,
        body,
      });

      respond(req, res);
    });
  });

  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();

      resolve({
        server,
        received,
        origin: `http://127.0.0.1:${port}`,
      });
    });
  });
}

const json = (res, status, payload) => {
  res.writeHead(status, {
    "content-type": "application/json",
  });

  res.end(JSON.stringify(payload));
};


/* ============================================================
 * RESPONSE HELPERS
 * ============================================================ */

const openAiReply = (text) => ({
  model: "stub-model",
  choices: [
    {
      message: {
        content: text,
      },
    },
  ],
});

const geminiReply = (text) => ({
  candidates: [
    {
      content: {
        parts: [
          {
            text,
          },
        ],
      },
    },
  ],
});

const openAiModelsReply = (models) => ({
  object: "list",
  data: models.map((id) => ({
    id,
    object: "model",
  })),
});


/* ============================================================
 * CLEANUP
 * ============================================================ */

const cleanup = [];

const track = (stub) => {
  cleanup.push(stub);
  return stub;
};

const closeAll = () => {
  for (const stub of cleanup) {
    stub.server.closeAllConnections?.();
    stub.server.close();
  }
};


/* ============================================================
 * TEST RUNNER
 * ============================================================ */

let passed = 0;

const tests = [];

const test = (name, fn) => {
  tests.push({
    name,
    fn,
  });
};


/* ============================================================
 * PROVIDER CHAIN
 * ============================================================ */

test(
  "resolveChain: hiçbir provider ayarlı değilse boş döner",
  () => {
    assert.deepEqual(
      resolveChain({}),
      [],
    );
  },
);

test(
  "resolveChain: OpenAI -> Gemini -> OpenRouter sırasını kullanır",
  () => {
    assert.deepEqual(
      resolveChain({
        OPENAI_API_KEY: "openai",
        GEMINI_API_KEY: "gemini",
        OPENROUTER_API_KEY: "openrouter",
      }),
      [
        "openai",
        "gemini",
        "openrouter",
      ],
    );
  },
);

test(
  "resolveChain: OpenAI anahtar yoksa otomatik atlanır",
  () => {
    assert.deepEqual(
      resolveChain({
        GEMINI_API_KEY: "gemini",
        OPENROUTER_API_KEY: "openrouter",
      }),
      [
        "gemini",
        "openrouter",
      ],
    );
  },
);

test(
  "resolveChain: yalnızca Gemini varsa Gemini kullanılır",
  () => {
    assert.deepEqual(
      resolveChain({
        GEMINI_API_KEY: "gemini",
      }),
      ["gemini"],
    );
  },
);

test(
  "resolveChain: yalnızca OpenRouter varsa OpenRouter kullanılır",
  () => {
    assert.deepEqual(
      resolveChain({
        OPENROUTER_API_KEY: "openrouter",
      }),
      ["openrouter"],
    );
  },
);

test(
  "resolveChain: AI_PROVIDER OpenAI'yi başa alabilir",
  () => {
    assert.deepEqual(
      resolveChain({
        OPENAI_API_KEY: "openai",
        GEMINI_API_KEY: "gemini",
        OPENROUTER_API_KEY: "openrouter",
        AI_PROVIDER: "openai",
      }),
      [
        "openai",
        "gemini",
        "openrouter",
      ],
    );
  },
);

test(
  "resolveChain: AI_PROVIDER Gemini'yi başa alabilir",
  () => {
    assert.deepEqual(
      resolveChain({
        OPENAI_API_KEY: "openai",
        GEMINI_API_KEY: "gemini",
        OPENROUTER_API_KEY: "openrouter",
        AI_PROVIDER: "gemini",
      }),
      [
        "gemini",
        "openai",
        "openrouter",
      ],
    );
  },
);

test(
  "resolveChain: AI_FALLBACK_ORDER özel sıra belirleyebilir",
  () => {
    assert.deepEqual(
      resolveChain({
        OPENAI_API_KEY: "openai",
        GEMINI_API_KEY: "gemini",
        OPENROUTER_API_KEY: "openrouter",
        AI_FALLBACK_ORDER:
          "openrouter,gemini,openai",
      }),
      [
        "openrouter",
        "gemini",
        "openai",
      ],
    );
  },
);


/* ============================================================
 * OPENAI MODEL DISCOVERY
 * ============================================================ */

test(
  "OpenAI: erişilebilir modelleri keşfeder ve uygun modeli seçer",
  async () => {
    const stub = track(
      await startStub((req, res) => {
        if (req.url === "/v1/models") {
          return json(
            res,
            200,
            openAiModelsReply([
              "text-embedding-3-small",
              "gpt-4o-mini",
              "moderation-latest",
              "gpt-5.6-terra",
            ]),
          );
        }

        if (
          req.url === "/v1/chat/completions"
        ) {
          return json(
            res,
            200,
            openAiReply(
              "OpenAI yanıtı",
            ),
          );
        }

        return json(
          res,
          404,
          {
            error: {
              message: "not found",
            },
          },
        );
      }),
    );

    const result = await runAI(
      {
        prompt: "LGS matematik sorusu",
      },
      {
        AI_PROVIDER: "openai",
        OPENAI_API_KEY: "test-openai-key",
        OPENAI_BASE_URL:
          `${stub.origin}/v1`,
      },
    );

    assert.equal(
      result.provider,
      "openai",
    );

    assert.equal(
      result.model,
      "gpt-5.6-terra",
    );

    assert.equal(
      result.text,
      "OpenAI yanıtı",
    );

    assert.equal(
      stub.received[0].url,
      "/v1/models",
    );

    assert.equal(
      stub.received[0].headers.authorization,
      "Bearer test-openai-key",
    );

    assert.equal(
      stub.received[1].url,
      "/v1/chat/completions",
    );

    assert.equal(
      stub.received[1].body.model,
      "gpt-5.6-terra",
    );
  },
);


/* ============================================================
 * OPENAI MODEL OVERRIDE
 * ============================================================ */

test(
  "OpenAI: OPENAI_MODEL verilirse model discovery yapılmaz",
  async () => {
    const stub = track(
      await startStub((req, res) => {
        if (
          req.url ===
          "/v1/chat/completions"
        ) {
          return json(
            res,
            200,
            openAiReply(
              "override yanıtı",
            ),
          );
        }

        return json(
          res,
          404,
          {},
        );
      }),
    );

    const result = await runAI(
      {
        prompt: "soru",
      },
      {
        AI_PROVIDER: "openai",
        OPENAI_API_KEY: "test-key",
        OPENAI_MODEL:
          "gpt-custom-model",
        OPENAI_BASE_URL:
          `${stub.origin}/v1`,
      },
    );

    assert.equal(
      result.provider,
      "openai",
    );

    assert.equal(
      result.model,
      "gpt-custom-model",
    );

    assert.equal(
      stub.received.length,
      1,
    );

    assert.equal(
      stub.received[0].url,
      "/v1/chat/completions",
    );
  },
);


/* ============================================================
 * OPENAI IMAGE
 * ============================================================ */

test(
  "OpenAI: metin + görsel gönderilebilir",
  async () => {
    const stub = track(
      await startStub((req, res) => {
        if (
          req.url === "/v1/models"
        ) {
          return json(
            res,
            200,
            openAiModelsReply([
              "gpt-4o-mini",
            ]),
          );
        }

        return json(
          res,
          200,
          openAiReply(
            "görsel analiz edildi",
          ),
        );
      }),
    );

    const result = await runAI(
      {
        prompt: "Bu soruyu analiz et",
        imageData:
          "data:image/png;base64,AAAA",
      },
      {
        AI_PROVIDER: "openai",
        OPENAI_API_KEY: "test-key",
        OPENAI_BASE_URL:
          `${stub.origin}/v1`,
      },
    );

    assert.equal(
      result.provider,
      "openai",
    );

    const request =
      stub.received.find(
        (item) =>
          item.url ===
          "/v1/chat/completions",
      );

    assert.ok(request);

    assert.equal(
      request.body.messages[0]
        .content[0].type,
      "text",
    );

    assert.equal(
      request.body.messages[0]
        .content[1].type,
      "image_url",
    );
  },
);


/* ============================================================
 * GEMINI
 * ============================================================ */

test(
  "Gemini: metin + görsel doğru gönderilir",
  async () => {
    const stub = track(
      await startStub((req, res) =>
        json(
          res,
          200,
          geminiReply(
            "Gemini yanıtı",
          ),
        ),
      ),
    );

    const result = await runAI(
      {
        prompt: "SORU",
        imageData:
          "data:image/png;base64,AAAA",
      },
      {
        AI_PROVIDER: "gemini",
        GEMINI_API_KEY: "test-key",
        GEMINI_BASE_URL:
          stub.origin,
      },
    );

    assert.equal(
      result.provider,
      "gemini",
    );

    assert.equal(
      result.model,
      "gemini-flash-latest",
    );

    assert.equal(
      result.text,
      "Gemini yanıtı",
    );

    assert.equal(
      stub.received[0].headers[
        "x-goog-api-key"
      ],
      "test-key",
    );
  },
);


/* ============================================================
 * OPENROUTER
 * ============================================================ */

test(
  "OpenRouter: chat completion yanıtı okunur",
  async () => {
    const stub = track(
      await startStub((req, res) =>
        json(
          res,
          200,
          openAiReply(
            "OpenRouter yanıtı",
          ),
        ),
      ),
    );

    const result = await runAI(
      {
        prompt: "soru",
      },
      {
        AI_PROVIDER:
          "openrouter",
        OPENROUTER_API_KEY:
          "test-key",
        OPENROUTER_BASE_URL:
          `${stub.origin}/v1`,
      },
    );

    assert.equal(
      result.provider,
      "openrouter",
    );

    assert.equal(
      result.model,
      "openrouter/free",
    );

    assert.equal(
      result.text,
      "OpenRouter yanıtı",
    );
  },
);


/* ============================================================
 * FALLBACK
 * ============================================================ */

test(
  "Fallback: OpenAI 500 -> Gemini başarılı",
  async () => {
    const openai = track(
      await startStub((req, res) =>
        json(
          res,
          500,
          {
            error: {
              message:
                "OpenAI temporary error",
            },
          },
        ),
      ),
    );

    const gemini = track(
      await startStub((req, res) =>
        json(
          res,
          200,
          geminiReply(
            "Gemini fallback",
          ),
        ),
      ),
    );

    const result = await runAI(
      {
        prompt: "soru",
      },
      {
        AI_FALLBACK_ORDER:
          "openai,gemini,openrouter",

        OPENAI_API_KEY:
          "openai-key",
        OPENAI_MODEL:
          "gpt-test",
        OPENAI_BASE_URL:
          `${openai.origin}/v1`,

        GEMINI_API_KEY:
          "gemini-key",
        GEMINI_BASE_URL:
          gemini.origin,

        OPENROUTER_API_KEY:
          "router-key",
      },
    );

    assert.equal(
      result.provider,
      "gemini",
    );

    assert.equal(
      result.text,
      "Gemini fallback",
    );

    assert.equal(
      openai.received.length,
      1,
    );

    assert.equal(
      gemini.received.length,
      1,
    );
  },
);


test(
  "Fallback: OpenAI 429 -> Gemini 500 -> OpenRouter başarılı",
  async () => {
    const openai = track(
      await startStub((req, res) =>
        json(
          res,
          429,
          {
            error: {
              message:
                "quota exceeded",
            },
          },
        ),
      ),
    );

    const gemini = track(
      await startStub((req, res) =>
        json(
          res,
          500,
          {
            error: {
              message:
                "Gemini temporary error",
            },
          },
        ),
      ),
    );

    const openrouter = track(
      await startStub((req, res) =>
        json(
          res,
          200,
          openAiReply(
            "OpenRouter fallback",
          ),
        ),
      ),
    );

    const result = await runAI(
      {
        prompt: "soru",
      },
      {
        AI_FALLBACK_ORDER:
          "openai,gemini,openrouter",

        OPENAI_API_KEY:
          "openai-key",
        OPENAI_MODEL:
          "gpt-test",
        OPENAI_BASE_URL:
          `${openai.origin}/v1`,

        GEMINI_API_KEY:
          "gemini-key",
        GEMINI_BASE_URL:
          gemini.origin,

        OPENROUTER_API_KEY:
          "router-key",
        OPENROUTER_BASE_URL:
          `${openrouter.origin}/v1`,
      },
    );

    assert.equal(
      result.provider,
      "openrouter",
    );

    assert.equal(
      result.text,
      "OpenRouter fallback",
    );

    assert.equal(
      openai.received.length,
      1,
    );

    assert.equal(
      gemini.received.length,
      1,
    );

    assert.equal(
      openrouter.received.length,
      1,
    );
  },
);


test(
  "Fallback: OpenAI timeout -> Gemini başarılı",
  async () => {
    const openai = track(
      await startStub(() => {
        // Yanıt vermiyor.
      }),
    );

    const gemini = track(
      await startStub((req, res) =>
        json(
          res,
          200,
          geminiReply(
            "timeout sonrası Gemini",
          ),
        ),
      ),
    );

    const result = await runAI(
      {
        prompt: "soru",
      },
      {
        AI_FALLBACK_ORDER:
          "openai,gemini",

        OPENAI_API_KEY:
          "openai-key",
        OPENAI_MODEL:
          "gpt-test",
        OPENAI_BASE_URL:
          `${openai.origin}/v1`,

        GEMINI_API_KEY:
          "gemini-key",
        GEMINI_BASE_URL:
          gemini.origin,

        AI_TIMEOUT_MS:
          "1200",
      },
    );

    assert.equal(
      result.provider,
      "gemini",
    );

    assert.equal(
      result.text,
      "timeout sonrası Gemini",
    );
  },
);


/* ============================================================
 * ALL FAILED
 * ============================================================ */

test(
  "Fallback: OpenAI + Gemini + OpenRouter başarısızsa AllProvidersFailed",
  async () => {
    const openai = track(
      await startStub((req, res) =>
        json(
          res,
          500,
          {
            error: {
              message: "OpenAI error",
            },
          },
        ),
      ),
    );

    const gemini = track(
      await startStub((req, res) =>
        json(
          res,
          429,
          {
            error: {
              message:
                "Gemini quota",
            },
          },
        ),
      ),
    );

    const openrouter = track(
      await startStub((req, res) =>
        json(
          res,
          503,
          {
            error: {
              message:
                "OpenRouter error",
            },
          },
        ),
      ),
    );

    await assert.rejects(
      () =>
        runAI(
          {
            prompt: "soru",
          },
          {
            AI_FALLBACK_ORDER:
              "openai,gemini,openrouter",

            OPENAI_API_KEY:
              "openai-key",
            OPENAI_MODEL:
              "gpt-test",
            OPENAI_BASE_URL:
              `${openai.origin}/v1`,

            GEMINI_API_KEY:
              "gemini-key",
            GEMINI_BASE_URL:
              gemini.origin,

            OPENROUTER_API_KEY:
              "router-key",
            OPENROUTER_BASE_URL:
              `${openrouter.origin}/v1`,
          },
        ),
      (error) => {
        assert.ok(
          error instanceof
            AllProvidersFailed,
        );

        assert.equal(
          error.status,
          502,
        );

        assert.deepEqual(
          error.attempts.map(
            (attempt) => [
              attempt.provider,
              attempt.status,
            ],
          ),
          [
            ["openai", 500],
            ["gemini", 429],
            ["openrouter", 503],
          ],
        );

        return true;
      },
    );
  },
);


/* ============================================================
 * TIMEOUT
 * ============================================================ */

test(
  "Timeout: provider timeout sonrası sıradakine geçer",
  async () => {
    const openai = track(
      await startStub(() => {
        // Yanıt yok.
      }),
    );

    const gemini = track(
      await startStub((req, res) =>
        json(
          res,
          200,
          geminiReply(
            "Gemini timeout fallback",
          ),
        ),
      ),
    );

    const result = await runAI(
      {
        prompt: "soru",
      },
      {
        AI_FALLBACK_ORDER:
          "openai,gemini",

        OPENAI_API_KEY:
          "openai-key",
        OPENAI_MODEL:
          "gpt-test",
        OPENAI_BASE_URL:
          `${openai.origin}/v1`,

        GEMINI_API_KEY:
          "gemini-key",
        GEMINI_BASE_URL:
          gemini.origin,

        AI_TIMEOUT_MS:
          "1200",
      },
    );

    assert.equal(
      result.provider,
      "gemini",
    );
  },
);


/* ============================================================
 * NO PROVIDER
 * ============================================================ */

test(
  "Yapılandırma yoksa ProviderError döner",
  async () => {
    await assert.rejects(
      () =>
        runAI(
          {
            prompt: "soru",
          },
          {},
        ),
      (error) =>
        error instanceof
          ProviderError &&
        error.status === 500,
    );
  },
);


/* ============================================================
 * RUN
 * ============================================================ */

try {
  for (const {
    name,
    fn,
  } of tests) {
    await fn();

    passed += 1;

    console.log(
      `  ✓ ${name}`,
    );
  }

  console.log(
    `\n${passed}/${tests.length} test geçti.`,
  );

  closeAll();
} catch (error) {
  closeAll();

  console.error(
    `\n  ✗ ${tests[passed]?.name ?? "bilinmeyen test"}\n`,
  );

  console.error(error);

  process.exitCode = 1;
}
