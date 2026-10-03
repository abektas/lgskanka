/**
 * AI sağlayıcı katmanı duman testi.
 *
 *   node scripts/ai-providers.smoke.mjs
 *
 * Gerçek ağa çıkmaz: her sağlayıcı için yerel bir taklit (stub) sunucu başlatılır.
 * Sağlayıcı seçimi, yedek zinciri, istek şekilleri ve hata mesajları doğrulanır.
 */

import assert from "node:assert/strict";
import http from "node:http";
import { AllProvidersFailed, ProviderError, resolveChain, runAI } from "../app/api/ai/providers.ts";

/** Gelen istekleri kaydeden tek yanıtlı taklit sunucu. */
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
        /* gövdesiz istek */
      }
      received.push({ url: req.url, method: req.method, headers: req.headers, body });
      respond(res);
    });
  });

  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      resolve({ server, received, origin: `http://127.0.0.1:${port}` });
    });
  });
}

const json = (res, status, payload) => {
  res.writeHead(status, { "content-type": "application/json" });
  res.end(JSON.stringify(payload));
};

const openAiReply = (text) => ({ model: "stub", choices: [{ message: { content: text } }] });
const geminiReply = (text) => ({ candidates: [{ content: { parts: [{ text }] } }] });

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

let passed = 0;
const tests = [];
const test = (name, fn) => tests.push({ name, fn });

// ---------------------------------------------------------------- sıra seçimi
test("resolveChain: hiçbir sağlayıcı ayarlı değilse boş döner", () => {
  assert.deepEqual(resolveChain({}), []);
});

test("resolveChain: ayarlı sağlayıcıları varsayılan sırada verir", () => {
  assert.deepEqual(resolveChain({ GEMINI_API_KEY: "g", OPENROUTER_API_KEY: "o" }), ["gemini", "openrouter"]);
});

test("resolveChain: AI_PROVIDER birincil sağlayıcıyı başa alır, yedekler korunur", () => {
  assert.deepEqual(
    resolveChain({ GEMINI_API_KEY: "g", OPENROUTER_API_KEY: "o", AI_PROVIDER: "openrouter" }),
    ["openrouter", "gemini"],
  );
  assert.deepEqual(
    resolveChain({ GEMINI_API_KEY: "g", OPENROUTER_API_KEY: "o", LOCAL_AI_BASE_URL: "http://x", AI_PROVIDER: "local" }),
    ["local", "gemini", "openrouter"],
  );
});

test("resolveChain: AI_FALLBACK_ORDER sırayı tamamen değiştirir, ayarsızlar atlanır", () => {
  assert.deepEqual(
    resolveChain({ AI_FALLBACK_ORDER: "local,openrouter,gemini", LOCAL_AI_BASE_URL: "http://x", GEMINI_API_KEY: "g" }),
    ["local", "gemini"],
  );
  // bilinmeyen adlar sessizce yok sayılır
  assert.deepEqual(resolveChain({ AI_FALLBACK_ORDER: "foo,openrouter", OPENROUTER_API_KEY: "o" }), ["openrouter"]);
});

test("resolveChain: AI_PROVIDER=auto varsayılan sırayı kullanır", () => {
  assert.deepEqual(
    resolveChain({ AI_PROVIDER: "auto", OPENROUTER_API_KEY: "o", LOCAL_AI_BASE_URL: "http://x" }),
    ["openrouter", "local"],
  );
});

// ------------------------------------------------------------------- gemini
test("gemini: metin + görsel doğru şekilde gönderilir, yanıt ayrıştırılır", async () => {
  const stub = track(await startStub((res) => json(res, 200, geminiReply("  Teşhis: H2 – yöntem eksiği.  "))));

  const result = await runAI(
    { prompt: "SORU: 2³ · 2⁵ = ?", imageData: "data:image/png;base64,AAAA" },
    { AI_PROVIDER: "gemini", GEMINI_API_KEY: "test-key", GEMINI_BASE_URL: stub.origin },
  );

  assert.equal(result.provider, "gemini");
  assert.equal(result.model, "gemini-flash-latest");
  assert.equal(result.text, "Teşhis: H2 – yöntem eksiği.");

  const [request] = stub.received;
  assert.equal(request.url, "/v1beta/models/gemini-flash-latest:generateContent");
  assert.equal(request.headers["x-goog-api-key"], "test-key");
  assert.equal(request.body.contents[0].parts[0].text, "SORU: 2³ · 2⁵ = ?");
  assert.deepEqual(request.body.contents[0].parts[1], { inline_data: { mime_type: "image/png", data: "AAAA" } });
  assert.equal(request.body.generationConfig.temperature, 0.2);
});

test("gemini: GEMINI_MODEL ile model değiştirilebilir, görsel eklenmezse parts tek olur", async () => {
  const stub = track(await startStub((res) => json(res, 200, geminiReply("tamam"))));

  await runAI({ prompt: "selam" }, { AI_PROVIDER: "gemini", GEMINI_API_KEY: "k", GEMINI_MODEL: "gemini-pro-latest", GEMINI_BASE_URL: stub.origin });

  assert.equal(stub.received[0].url, "/v1beta/models/gemini-pro-latest:generateContent");
  assert.equal(stub.received[0].body.contents[0].parts.length, 1);
});

test("gemini: içerik engellenirse açıklayıcı hata verir", async () => {
  const stub = track(await startStub((res) => json(res, 200, { promptFeedback: { blockReason: "SAFETY" } })));

  await assert.rejects(
    () => runAI({ prompt: "x" }, { AI_PROVIDER: "gemini", GEMINI_API_KEY: "k", GEMINI_BASE_URL: stub.origin }),
    (error) => error instanceof AllProvidersFailed && /engelledi \(SAFETY\)/.test(error.message),
  );
});

// --------------------------------------------------------------- openrouter
test("openrouter: OpenAI uyumu gövde + ham base64 görsel data URI'ye çevrilir", async () => {
  const stub = track(await startStub((res) => json(res, 200, openAiReply("OpenRouter yanıtı"))));

  const result = await runAI(
    { prompt: "soru", imageData: "BBBB" },
    { AI_PROVIDER: "openrouter", OPENROUTER_API_KEY: "sk-test", OPENROUTER_BASE_URL: `${stub.origin}/api/v1` },
  );

  assert.equal(result.provider, "openrouter");
  assert.equal(result.model, "openrouter/free");
  assert.equal(result.text, "OpenRouter yanıtı");

  const [request] = stub.received;
  assert.equal(request.url, "/api/v1/chat/completions");
  assert.equal(request.headers.authorization, "Bearer sk-test");
  assert.equal(request.headers["x-title"], "LGS AI Coach"); // ASCII olmalı: Türkçe karakter başlıkta isteği çökertir
  assert.equal(request.body.messages[0].content[0].type, "text");
  assert.equal(request.body.messages[0].content[1].image_url.url, "data:image/jpeg;base64,BBBB");
});

// -------------------------------------------------------------------- local
test("local: /chat/completions adresine istek atar, model ve api key aktarılır", async () => {
  const stub = track(await startStub((res) => json(res, 200, openAiReply("Yerel yanıt"))));

  const result = await runAI(
    { prompt: "soru" },
    {
      AI_PROVIDER: "local",
      LOCAL_AI_BASE_URL: `${stub.origin}/v1/`,
      LOCAL_AI_MODEL: "qwen3-8b",
      LOCAL_AI_API_KEY: "local-secret",
    },
  );

  assert.equal(result.provider, "local");
  assert.equal(result.model, "qwen3-8b");
  assert.equal(result.text, "Yerel yanıt");

  const [request] = stub.received;
  assert.equal(request.url, "/v1/chat/completions");
  assert.equal(request.headers.authorization, "Bearer local-secret");
  assert.equal(request.body.model, "qwen3-8b");
  assert.equal(request.body.messages[0].content.length, 1);
});

// ----------------------------------------------------------------- yedekleme
test("yedek zinciri: gemini 500 → openrouter 429 → local 200 (sıralı geçiş)", async () => {
  const gemini = track(await startStub((res) => json(res, 500, { error: { message: "gemini çöktü" } })));
  const openrouter = track(await startStub((res) => json(res, 429, { error: { message: "kota doldu" } })));
  const local = track(await startStub((res) => json(res, 200, openAiReply("yerelden geldi"))));

  const result = await runAI(
    { prompt: "soru" },
    {
      AI_PROVIDER: "gemini",
      GEMINI_API_KEY: "g",
      GEMINI_BASE_URL: gemini.origin,
      OPENROUTER_API_KEY: "o",
      OPENROUTER_BASE_URL: `${openrouter.origin}/api/v1`,
      LOCAL_AI_BASE_URL: `${local.origin}/v1`,
    },
  );

  assert.equal(result.provider, "local");
  assert.equal(result.text, "yerelden geldi");
  assert.equal(gemini.received.length, 1);
  assert.equal(openrouter.received.length, 1);
  assert.equal(local.received.length, 1);
});

test("yedek zinciri: hepsi düşerse denemelerin sebebiyle birlikte hata verir", async () => {
  const gemini = track(await startStub((res) => json(res, 500, { error: { message: "gemini çöktü" } })));
  const openrouter = track(await startStub((res) => json(res, 429, { error: { message: "kota doldu" } })));

  await assert.rejects(
    () =>
      runAI(
        { prompt: "soru" },
        {
          AI_PROVIDER: "gemini",
          GEMINI_API_KEY: "g",
          GEMINI_BASE_URL: gemini.origin,
          OPENROUTER_API_KEY: "o",
          OPENROUTER_BASE_URL: `${openrouter.origin}/api/v1`,
          LOCAL_AI_BASE_URL: "http://127.0.0.1:1/v1", // kapalı port → ağ hatası
        },
      ),
    (error) => {
      assert.ok(error instanceof AllProvidersFailed, "AllProvidersFailed bekleniyordu");
      assert.equal(error.status, 502);
      assert.deepEqual(
        error.attempts.map((a) => [a.provider, a.status]),
        [
          ["gemini", 500],
          ["openrouter", 429],
          ["local", null],
        ],
      );
      assert.match(error.attempts[0].error, /gemini çöktü/);
      assert.match(error.attempts[2].error, /bağlantı kurulamadı/);
      return true;
    },
  );
});

test("zaman aşımı: yanıt vermeyen sağlayıcı AI_TIMEOUT_MS sonra düşer", async () => {
  const stub = track(await startStub(() => {})); // hiç yanıt vermez

  await assert.rejects(
    () =>
      runAI(
        { prompt: "soru" },
        { AI_PROVIDER: "local", LOCAL_AI_BASE_URL: `${stub.origin}/v1`, AI_TIMEOUT_MS: "1200" },
      ),
    (error) => error instanceof AllProvidersFailed && /zaman aşımı/.test(error.attempts[0].error),
  );
});

test("yapılandırma yok: kurulum talimatı içeren 500 hatası verir", async () => {
  await assert.rejects(
    () => runAI({ prompt: "soru" }, {}),
    (error) => error instanceof ProviderError && error.status === 500 && /GEMINI_API_KEY/.test(error.message),
  );
});

// ---------------------------------------------------------------------- koşu
try {
  for (const { name, fn } of tests) {
    await fn();
    passed += 1;
    console.log(`  ✓ ${name}`);
  }
  console.log(`\n${passed}/${tests.length} test geçti.`);
  closeAll();
} catch (error) {
  closeAll();
  console.error(`\n  ✗ ${tests[passed].name}\n`);
  console.error(error);
  process.exitCode = 1;
}
