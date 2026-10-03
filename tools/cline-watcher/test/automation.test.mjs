/**
 * TASK-AUTOMATION-002 testleri — sürekli otomasyon, event tetikleme, health,
 * graceful shutdown.
 *
 * Gerçek ağ/Cline/repo kullanılmaz; stub binler ve geçici dizinlerle çalışır.
 */
import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { mkdtempSync, existsSync, readFileSync, writeFileSync, chmodSync } from "node:fs";
import { tmpdir } from "node:os";

import { createTriggerServer, signPayload } from "../lib/webhook.mjs";
import { createHealthReporter, readHealthFile } from "../lib/health.mjs";
import { DEFAULTS } from "../lib/config.mjs";
import { runCline } from "../lib/runner.mjs";

const tmpState = () => mkdtempSync(path.join(tmpdir(), "cw-health-"));

// --- event (webhook) tetikleyicisi -----------------------------------------

test("event: geçerli imzalı POST tetikler", async () => {
  const secret = "test-secret-not-real";
  const seen = [];
  const srv = createTriggerServer({
    secret, port: 0, path: "/cline-trigger", onTrigger: (e) => seen.push(e),
  });
  const { port } = await srv.start();
  const body = JSON.stringify({ zenhook_event: "issues", issue: { number: 3 } });
  const res = await fetch(`http://127.0.0.1:${port}/cline-trigger`, {
    method: "POST",
    headers: { "x-hub-signature-256": signPayload(body, secret) },
    body,
  });
  assert.equal(res.status, 202);
  await srv.close();
  assert.equal(seen.length, 1);
  assert.equal(seen[0].event, "issues");
  assert.equal(seen[0].issueNumber, 3);
});

test("event: imzasız/yanlış imzalı istek REDDEDİLİR (fail-closed)", async () => {
  const secret = "test-secret-not-real";
  const seen = [];
  const srv = createTriggerServer({ secret, port: 0, onTrigger: (e) => seen.push(e) });
  const { port } = await srv.start();
  const body = JSON.stringify({ zenhook_event: "issues" });

  const noSig = await fetch(`http://127.0.0.1:${port}/cline-trigger`, { method: "POST", body });
  assert.equal(noSig.status, 401);
  const badSig = await fetch(`http://127.0.0.1:${port}/cline-trigger`, {
    method: "POST",
    headers: { "x-hub-signature-256": `sha256=${"0".repeat(64)}` },
    body,
  });
  assert.equal(badSig.status, 401);
  await srv.close();
  assert.equal(seen.length, 0, "geçersiz istek tetiklememeli");
});

test("event: secret yoksa sunucu BAŞLAMAZ (fail-closed)", () => {
  assert.throws(
    () => createTriggerServer({ port: 0 }),
    /secret/,
    "secret yoksa webhook alıcısı başlamamalı (fail-closed)",
  );
});

test("event: yalnız POST ve yalnız yapılandırılmış yol kabul edilir", async () => {
  const secret = "test-secret-not-real";
  const seen = [];
  const srv = createTriggerServer({ secret, port: 0, path: "/cline-trigger", onTrigger: (e) => seen.push(e) });
  const { port } = await srv.start();
  const wrongPath = await fetch(`http://127.0.0.1:${port}/other`, { method: "POST", body: "{}" });
  assert.equal(wrongPath.status, 404);
  const get = await fetch(`http://127.0.0.1:${port}/cline-trigger`);
  assert.equal(get.status, 404);
  await srv.close();
  assert.equal(seen.length, 0);
});

test("event: aşırı büyük gövde reddedilir (DoS koruması)", async () => {
  const secret = "test-secret-not-real";
  const srv = createTriggerServer({ secret, port: 0, maxBodyBytes: 64, onTrigger: () => {} });
  const { port } = await srv.start();
  const res = await fetch(`http://127.0.0.1:${port}/cline-trigger`, {
    method: "POST",
    headers: { "x-hub-signature-256": signPayload("x".repeat(4096), secret) },
    body: "x".repeat(4096),
  }).catch(() => ({ status: 413 }));
  assert.equal(res.status, 413);
  await srv.close();
});

// --- health / status -------------------------------------------------------

test("health: durum dosyası yazılır ve gizli veri içermez", () => {
  const stateDir = tmpState();
  const h = createHealthReporter({ stateDir, intervalSec: 240, triggerMode: "fallback" });
  h.flush();
  h.roundStart({ source: "poll" });
  h.taskStarted({ taskId: "TASK-X-1", issueNumber: 7 });
  h.taskFinished({ taskId: "TASK-X-1", issueNumber: 7 });
  h.roundFinished({ status: "ok" });

  const file = path.join(stateDir, "health.json");
  assert.ok(existsSync(file));
  const raw = readFileSync(file, "utf8");
  const parsed = JSON.parse(raw);

  assert.equal(parsed.fallbackIntervalSec, 240);
  assert.equal(parsed.triggerMode, "fallback");
  assert.equal(parsed.polls, 1);
  assert.equal(parsed.runningTask, null);
  assert.equal(parsed.lastRoundStatus, "ok");
  assert.ok(!/gh[pousr]_|READY_FOR_CLINE/.test(raw), "gövde/secret sızmamalı");
  assert.equal(readHealthFile(stateDir).pid, parsed.pid);
});

test("health: tur hatası sayacı artar, shutdown temizlenir", () => {
  const stateDir = tmpState();
  const h = createHealthReporter({ stateDir, intervalSec: 240, triggerMode: "fallback" });
  h.roundFinished({ status: "error", error: "boom" });
  assert.equal(h.read().roundFailures, 1);
  assert.equal(h.read().consecutiveFailures, 1);
  h.taskStarted({ taskId: "TASK-Y-1", issueNumber: 9 });
  h.shutdown();
  assert.equal(h.read().runningTask, null);
  assert.equal(h.read().lastRoundStatus, "shutdown");
});

test("health: event turu polls değil eventsReceived sayar", () => {
  const stateDir = tmpState();
  const h = createHealthReporter({ stateDir, intervalSec: 240, triggerMode: "event+fallback" });
  h.roundStart({ source: "event", eventType: "issues" });
  h.roundFinished({ status: "ok" });
  assert.equal(h.read().eventsReceived, 1);
  assert.equal(h.read().polls, 0);
  assert.equal(h.read().lastEventType, "issues");
  assert.ok(h.read().lastTriggerAt);
});

// --- config / fallback aralığı --------------------------------------------

test("config: fallback aralığı 3–5 dk hedefinde", () => {
  assert.ok(DEFAULTS.fallbackIntervalSec >= 180 && DEFAULTS.fallbackIntervalSec <= 300,
    `fallbackIntervalSec 3–5 dk aralığında olmalı, got ${DEFAULTS.fallbackIntervalSec}`);
  assert.equal(DEFAULTS.fallbackIntervalSec, 240, "seçilen değer 4 dk ve DÖKÜMANTASYONDA");
  assert.equal(DEFAULTS.minPollIntervalSec, 60);
});

test("config: event varsayılan kapalı, loopback + secret ENV ADI kullanır", () => {
  assert.equal(DEFAULTS.eventWebhook.enabled, false);
  assert.equal(DEFAULTS.eventWebhook.host, "127.0.0.1", "yalnız loopback dinlemeli");
  assert.equal(DEFAULTS.eventWebhook.secretEnv, "CLINE_WATCHER_WEBHOOK_SECRET");
});

// --- graceful shutdown: çalışan Cline süreci -------------------------------

/** Verilen süre boyunca çalışan, SIGTERM'e duyarlı sahte cline. */
const SLOW_CLINE = `#!/usr/bin/env node
if (process.argv.includes("--version")) { console.log("cline-stub 3.0.62"); process.exit(0); }
process.on("SIGTERM", () => { process.stdout.write('{"type":"run_result","finishReason":"aborted"}\\n'); process.exit(0); });
setTimeout(() => { process.exit(1); }, 60000);
`;

test("shutdown: çalışan Cline süreci abort() ile durur, sonuç 'interrupted'", async () => {
  const bin = mkdtempSync(path.join(tmpdir(), "cw-cline-"));
  const clineBin = path.join(bin, "cline");
  writeFileSync(clineBin, SLOW_CLINE);
  chmodSync(clineBin, 0o755);

  let abort = null;
  const promise = runCline({
    clineBin, repoPath: bin, prompt: "p", timeoutSec: 600, timeoutGraceSec: 5,
    autoApprove: true,
    onSpawn: (a) => { abort = a; },
  });

  for (let i = 0; i < 100 && !abort; i += 1) await new Promise((r) => setTimeout(r, 20));
  assert.equal(typeof abort, "function", "onSpawn abort kancası vermeli");

  abort("shutdown");
  const result = await promise;
  assert.equal(result.aborted, true);
  assert.equal(result.outcome, "interrupted");
  assert.notEqual(result.outcome, "succeeded", "shutdown başarı SAYILMAMALI");
  assert.equal(result.timedOut, false);
});

test("runner: çıktı yoksa başarı sayılmaz", async () => {
  const result = await runCline({
    clineBin: "/bin/true", repoPath: tmpdir(), prompt: "p", timeoutSec: 5, autoApprove: false,
  });
  assert.equal(result.outcome, "failed");
  assert.equal(result.aborted, false);
});

test("event: GET ve yanlış yol reddedilir", async () => {
  const srv = createTriggerServer({ secret: "s", port: 0, path: "/cline-trigger" });
  const { port } = await srv.start();
  assert.equal((await fetch(`http://127.0.0.1:${port}/cline-trigger`)).status, 404);
  assert.equal((await fetch(`http://127.0.0.1:${port}/other`)).status, 404);
  await srv.close();
});

test("event: aşırı büyük gövde 413 ile sınırlandırılır", async () => {
  const secret = "s";
  const srv = createTriggerServer({ secret, port: 0, maxBodyBytes: 512 });
  const { port } = await srv.start();
  const body = JSON.stringify({ zenhook_event: "issues", pad: "x".repeat(2000) });
  const res = await fetch(`http://127.0.0.1:${port}/cline-trigger`, {
    method: "POST",
    headers: { "x-hub-signature-256": signPayload(body, secret) },
    body,
  });
  assert.equal(res.status, 413);
  await srv.close();
});