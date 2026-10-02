/**
 * Yapılandırılmış günlük (structured log).
 *
 * Kurallar:
 *  - Yalnız tanımlayıcı/durum alanları yazılır.
 *  - Issue gövdesi, token, secret veya öğrenci verisi ASLA yazılmaz.
 *  - Dosyalar 0600 izinle oluşturulur.
 */
import { appendFileSync, mkdirSync } from "node:fs";
import path from "node:path";

const REDACT_KEYS = /(token|secret|api[_-]?key|authorization|password|body|prompt|task_text)/i;

export function createLogger({ logDir, dryRun = true }) {
  mkdirSync(logDir, { recursive: true, mode: 0o700 });
  const file = path.join(logDir, `watcher-${new Date().toISOString().replace(/[:.]/g, "-")}.log`);

  function write(level, event, fields = {}) {
    const safe = {};
    for (const [key, value] of Object.entries(fields)) {
      if (REDACT_KEYS.test(key)) {
        safe[key] = "[redacted]";
      } else if (typeof value === "string" && value.length > 300) {
        safe[key] = `${value.slice(0, 300)}…`;
      } else {
        safe[key] = value;
      }
    }
    const line = JSON.stringify({
      ts: new Date().toISOString(),
      level,
      dryRun,
      event,
      ...safe,
    });
    appendFileSync(file, `${line}\n`, { mode: 0o600 });
    if (!process.env.CLINE_WATCHER_QUIET) {
      process.stdout.write(`${level.toUpperCase()} ${event} ${JSON.stringify(safe)}\n`);
    }
    return line;
  }

  return {
    file,
    info: (event, fields) => write("info", event, fields),
    warn: (event, fields) => write("warn", event, fields),
    error: (event, fields) => write("error", event, fields),
    /** Cline NDJSON ham çıktısı için ayrı dosya (ayrı izin, ayrı yol). */
    clineStream: (name, text) => {
      const target = path.isAbsolute(name) ? name : path.join(logDir, name);
      mkdirSync(path.dirname(target), { recursive: true, mode: 0o700 });
      appendFileSync(target, text, { mode: 0o600 });
      return target;
    },
  };
}
