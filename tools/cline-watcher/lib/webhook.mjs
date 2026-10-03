/**
 * Yerel event (webhook) tetikleyicisi — TASK-AUTOMATION-002.
 *
 * Amaç: GitHub'daki uygun bir olay olduğunda watcher'a **derhal** "şimdi tara"
 * sinyali vermek. Tam yetkilendirme YİNE `lib/github.mjs` içinde yapılır; burada
 * gelen olay yalnız bir TETİK sinyali olup görev çalıştırma yetkisi vermez.
 * Böylece event yolu atlanırsa da güvenlik sözleşmesi gevşemez.
 *
 * Güvenlik:
 *  - HMAC-SHA256 (`X-Hub-Signature-256`) doğrulanır; secret ortam değişkeninden
 *    okunur, hiçbir yere yazılmaz. Secret yoksa sunucu BAŞLAMAZ (fail-closed).
 *  - Yalnız POST + yalnız yapılandırılmış yol; gövde boyutu üst sınırı.
 *  - Olay gövdesi loglanmaz, state'e yazılmaz; yalnız tür/numara sayılır.
 *  - Gövde içeriği hiçbir koşulda komut olarak yorumlanmaz.
 */
import { createHmac, timingSafeEqual } from "node:crypto";
import http from "node:http";

/** GitHub'ın imza biçimi: sha256=<hex> */
function verifySignature(rawBody, headerValue, secret) {
  if (typeof headerValue !== "string" || !headerValue.startsWith("sha256=")) return false;
  const expected = createHmac("sha256", secret).update(rawBody).digest("hex");
  const provided = headerValue.slice("sha256=".length);
  if (provided.length !== expected.length) return false;
  try {
    return timingSafeEqual(Buffer.from(provided, "utf8"), Buffer.from(expected, "utf8"));
  } catch {
    return false;
  }
}

function safeJson(res, code, body) {
  const payload = JSON.stringify(body);
  res.writeHead(code, { "content-type": "application/json", "cache-control": "no-store" });
  res.end(payload);
}

/**
 * @returns {{server: import("node:http").Server, start: Promise<{port:number}>}}
 */
export function createTriggerServer({ secret, host = "127.0.0.1", port = 0, path = "/cline-trigger",
  maxBodyBytes = 64 * 1024, onTrigger, onLog } = {}) {
  if (!secret) throw new Error("event webhook secret gerekli (fail-closed)");

  const server = http.createServer((req, res) => {
    if (req.method !== "POST" || (req.url ?? "").split("?")[0] !== path) {
      // Kısa yollar (health dışındaki her şey) loglanmaz.
      safeJson(res, 404, { ok: false, error: "not_found" });
      return;
    }

    const chunks = [];
    let size = 0;
    let aborted = false;
    req.on("data", (chunk) => {
      if (aborted) return;
      size += chunk.length;
      if (size > maxBodyBytes) {
        aborted = true;
        onLog?.("event_payload_too_large", { maxBodyBytes });
        safeJson(res, 413, { ok: false, error: "payload_too_large" });
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });

    req.on("end", () => {
      if (aborted) return;
      const raw = Buffer.concat(chunks).toString("utf8");
      if (!verifySignature(raw, req.headers["x-hub-signature-256"], secret)) {
        onLog?.("event_rejected", { reason: "bad_signature" });
        safeJson(res, 401, { ok: false, error: "unauthorized" });
        return;
      }

      // Gövde YALNIZ tetik türü için ayrıştırılır; içerik kullanılmaz.
      let event = "unknown";
      let issueNumber = null;
      try {
        const parsed = JSON.parse(raw || "{}");
        if (typeof parsed.zenhook_event === "string") event = parsed.zenhook_event;
        else if (typeof parsed.hook_event_type === "string") event = parsed.hook_event_type;
        if (Number.isInteger(parsed.issue?.number)) issueNumber = parsed.issue.number;
      } catch {
        onLog?.("event_rejected", { reason: "unparsable_payload" });
        safeJson(res, 400, { ok: false, error: "bad_payload" });
        return;
      }

      onLog?.("event_received", { event, issueNumber });
      try {
        onTrigger?.({ event, issueNumber });
      } catch {
        /* tetik hatayı yutmaz; döngü kendi hata kurtarmasını yapar */
      }
      safeJson(res, 202, { ok: true, queued: true });
    });
  });

  return {
    server,
    start: () => new Promise((resolve, reject) => {
      server.once("error", reject);
      server.listen(port, host, () => resolve({ port: server.address().port }));
    }),
    close: () => new Promise((resolve) => server.close(() => resolve(true))),
  };
}

/** Test/CLI yardımı: ham gövdenin geçerli imzasını üretir (secret yalnız bellekte). */
export function signPayload(rawBody, secret) {
  return `sha256=${createHmac("sha256", secret).update(rawBody).digest("hex")}`;
}