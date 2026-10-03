/**
 * Gözlemlenebilirlik (health / status) — TASK-AUTOMATION-002 gereksinimi 12.
 *
 * Kalıcı, atomik `state/health.json`: watcher'ın canlı olup olmadığı, son
 * yoklamanın ne zaman/yoldan yapıldığı, çalışan görev ve son tur sonucu.
 *
 * Gizlilik: burada YALNIZ tanımlayıcılar, zaman damgaları, sayaçlar ve durumlar
 * bulunur. Issue gövdesi, prompt, token, öğrenci verisi ASLA yazılmaz.
 */
import { mkdirSync, readFileSync, writeFileSync, renameSync, existsSync } from "node:fs";
import path from "node:path";

export const HEALTH_SCHEMA_VERSION = 1;

export function createHealthReporter({ stateDir, intervalSec, triggerMode }) {
  mkdirSync(stateDir, { recursive: true, mode: 0o700 });
  const file = path.join(stateDir, "health.json");

  const health = {
    schemaVersion: HEALTH_SCHEMA_VERSION,
    pid: process.pid,
    startedAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    triggerMode,
    fallbackIntervalSec: intervalSec,
    eventsReceived: 0,
    polls: 0,
    roundFailures: 0,
    lastPollAt: null,
    lastTriggerAt: null,
    lastTriggerSource: null,
    lastEventType: null,
    lastRoundStatus: null,
    lastRoundError: null,
    runningTask: null,
    consecutiveFailures: 0,
  };

  function flush() {
    health.updatedAt = new Date().toISOString();
    const tmp = `${file}.tmp-${process.pid}`;
    writeFileSync(tmp, `${JSON.stringify(health, null, 2)}\n`, { mode: 0o600 });
    renameSync(tmp, file);
    return health;
  }

  return {
    file,
    read: () => health,
    flush,
    roundStart({ source, eventType = null }) {
      if (source === "event") {
        health.eventsReceived += 1;
        health.lastTriggerAt = new Date().toISOString();
        health.lastEventType = eventType;
      } else {
        health.polls += 1;
        health.lastPollAt = new Date().toISOString();
      }
      health.lastTriggerSource = source;
      health.lastRoundError = null;
      health.consecutiveFailures = 0;
      return flush();
    },
    taskStarted({ taskId, issueNumber, startedAt }) {
      health.runningTask = { taskId, issueNumber, startedAt: startedAt ?? new Date().toISOString() };
      return flush();
    },
    taskFinished({ taskId, issueNumber }) {
      if (health.runningTask?.taskId === taskId && health.runningTask?.issueNumber === issueNumber) {
        health.runningTask = null;
      }
      return flush();
    },
    roundFinished({ status, error = null }) {
      health.lastRoundStatus = status;
      if (error) {
        health.lastRoundError = String(error).slice(0, 200);
        health.roundFailures += 1;
        health.consecutiveFailures += 1;
      }
      return flush();
    },
    shutdown() {
      health.runningTask = null;
      health.lastRoundStatus = "shutdown";
      return flush();
    },
  };
}

/** `--status` için mevcut health verisini okur (dosya yoksa null). */
export function readHealthFile(stateDir) {
  const file = path.join(stateDir, "health.json");
  if (!existsSync(file)) return null;
  try {
    return JSON.parse(readFileSync(file, "utf8"));
  } catch {
    return null;
  }
}