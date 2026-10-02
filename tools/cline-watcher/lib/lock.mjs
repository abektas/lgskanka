/**
 * Tek-instance kilidi.
 *
 * İzleyici aynı anda yalnız bir kopya çalışır (Issue #1: "must not automatically
 * start a second task while a prior task is active"). Kilit dosyası O_EXCL ile
 * oluşturulur; süreç ölüyse (stale) kilit güvenli biçimde devralınır.
 */
import { openSync, closeSync, writeSync, readFileSync, unlinkSync, existsSync } from "node:fs";
import path from "node:path";
import { mkdirSync } from "node:fs";

function isAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (err) {
    return err?.code === "EPERM"; // başka kullanıcıya ait ama yaşıyor
  }
}

export function acquireLock(stateDir) {
  mkdirSync(stateDir, { recursive: true, mode: 0o700 });
  const lockPath = path.join(stateDir, "watcher.lock");

  const tryCreate = () => {
    const fd = openSync(lockPath, "wx", 0o600);
    writeSync(fd, JSON.stringify({ pid: process.pid, startedAt: new Date().toISOString() }));
    closeSync(fd);
    return true;
  };

  if (!existsSync(lockPath)) {
    tryCreate();
    return { path: lockPath, acquired: true, released: false };
  }

  let holder = null;
  try {
    holder = JSON.parse(readFileSync(lockPath, "utf8"));
  } catch {
    holder = null;
  }

  if (holder && isAlive(holder.pid)) {
    return { path: lockPath, acquired: false, holder };
  }

  // Ölü sahibin kilidi: güvenli biçimde devral.
  try {
    unlinkSync(lockPath);
  } catch {
    /* yarış durumu */
  }
  try {
    tryCreate();
    return { path: lockPath, acquired: true, released: true, staleHolder: holder };
  } catch {
    return { path: lockPath, acquired: false, holder };
  }
}

export function releaseLock(lock) {
  if (!lock?.acquired) return false;
  try {
    unlinkSync(lock.path);
    lock.released = true;
    return true;
  } catch {
    return false;
  }
}
