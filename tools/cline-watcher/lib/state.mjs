/**
 * Kalıcı görev durumu (restart sonrası korunur).
 *
 * - Atomik yazım: geçici dosya + rename.
 * - Duplicate koruması: aynı taskId+issueNumber ikinci kez çalıştırılamaz.
 * - Durumlar: claimed | running | succeeded | failed | timeout | interrupted | rejected
 */
import { mkdirSync, readFileSync, writeFileSync, renameSync, existsSync } from "node:fs";
import path from "node:path";

/** Terminal (görev bitti) durumlar. */
export const TERMINAL_STATUSES = ["succeeded", "failed", "timeout", "rejected", "interrupted"];
/** Hâlâ süren durumlar. */
export const ACTIVE_STATUSES = ["claimed", "running"];
/**
 * Yalnız bunlar duplicate sayılır — yani görev tamamlandı, tekrar çalıştırılırsa
 * aynı iş iki kez yapılır. `failed` / `timeout` / `interrupted` burada YOKTUR:
 * bu görevler başarısız bitmiştir ve yeniden denenmelidir.
 */
export const SUCCESS_STATUSES = ["succeeded"];

export function createStore(stateDir) {
  mkdirSync(stateDir, { recursive: true, mode: 0o700 });
  const file = path.join(stateDir, "tasks.json");

  function read() {
    if (!existsSync(file)) return { schemaVersion: 1, tasks: {} };
    try {
      const parsed = JSON.parse(readFileSync(file, "utf8"));
      if (!parsed || typeof parsed !== "object" || !parsed.tasks) return { schemaVersion: 1, tasks: {} };
      return parsed;
    } catch {
      // Bozuk state: sessizce sıfırlamak yerine dosyayı koruyup boş başlat.
      return { schemaVersion: 1, tasks: {} };
    }
  }

  function write(state) {
    const tmp = `${file}.tmp-${process.pid}`;
    writeFileSync(tmp, `${JSON.stringify(state, null, 2)}\n`, { mode: 0o600 });
    renameSync(tmp, file);
    return file;
  }

  return {
    file,
    read,
    write,
    key(taskId, issueNumber) {
      return `${taskId}#${issueNumber}`;
    },
    get(taskId, issueNumber) {
      return read().tasks[this.key(taskId, issueNumber)] ?? null;
    },
    /**
 * Duplicate kontrolü.
 *
 * Yalnız görevin BAŞARILI bitmiş olduğu durumda duplicate sayılır.
 * `failed` / `timeout` / `interrupted` görevler yeniden çalıştırılabilir:
 * aksi halde izleyici tek bir hatalı koşumdan sonra o görevi kalıcı olarak
 * kilitler ve hiç tamamlanamaz. `rejected` de tekrar denemeye açıktır
 * (gövde düzeltilip yeniden etiketlenebilir).
 */
isDuplicate(taskId, issueNumber) {
      const entry = this.get(taskId, issueNumber);
      return entry !== null && SUCCESS_STATUSES.includes(entry.status);
    },
    upsert(taskId, issueNumber, patch) {
      const state = read();
      const key = this.key(taskId, issueNumber);
      const previous = state.tasks[key] ?? {};
      state.tasks[key] = {
        ...previous,
        ...patch,
        taskId,
        issueNumber,
        updatedAt: new Date().toISOString(),
        createdAt: previous.createdAt ?? new Date().toISOString(),
      };
      write(state);
      return state.tasks[key];
    },
    /** Restart sonrası yarım kalan görevleri işaretle (interrupted). */
    reconcileInterrupted() {
      const state = read();
      let changed = 0;
      for (const entry of Object.values(state.tasks)) {
        if (ACTIVE_STATUSES.includes(entry.status)) {
          entry.status = "interrupted";
          entry.note = "watcher restarted while task was active";
          entry.updatedAt = new Date().toISOString();
          changed += 1;
        }
      }
      if (changed > 0) write(state);
      return changed;
    },
    list() {
      return Object.values(read().tasks);
    },
  };
}
