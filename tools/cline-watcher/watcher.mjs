#!/usr/bin/env node
/**
 * TASK-AUTOMATION-001/002 — GitHub → Cline CLI task watcher/runner.
 *
 * Akış: GitHub Issue → keşif → yetkilendirme → duplicate → güvenli prompt →
 *       Cline CLI headless → NDJSON/run_result → kalıcı state/log.
 *
 * Tetikleme (TASK-AUTOMATION-002):
 *   - tercih edilen: event-driven (yerel webhook alıcısı, HMAC doğrulamalı)
 *   - fallback: `--interval` / `fallbackIntervalSec` (240 sn = 4 dk)
 *
 * Güvenlik varsayılanları: dry-run AÇIK, Cline `--auto-approve true` (PO onayı),
 * tek instance, gövde asla komut olarak çalıştırılmaz, doğrulama başarısızsa
 * FAIL CLOSED. Event yolu yalnız "şimdi tara" sinyali verir; yetkilendirme
 * yine `lib/github.mjs` içinde aynı kapılardan geçer.
 *
 * Kullanım:
 *   node tools/cline-watcher/watcher.mjs --dry-run
 *   node tools/cline-watcher/watcher.mjs --execute
 *   node tools/cline-watcher/watcher.mjs --interval 240
 *   node tools/cline-watcher/watcher.mjs --interval 240 --event-webhook
 *   node tools/cline-watcher/watcher.mjs --preflight-only
 *   node tools/cline-watcher/watcher.mjs --status
 *   node tools/cline-watcher/watcher.mjs --install-systemd | --uninstall-systemd
 */
import path from "node:path";
import { pathToFileURL } from "node:url";
import { execFileSync, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync, copyFileSync } from "node:fs";

import { loadConfig, resolveBin, TOOL_ROOT } from "./lib/config.mjs";
import { createLogger } from "./lib/log.mjs";
import { acquireLock, releaseLock } from "./lib/lock.mjs";
import { createStore } from "./lib/state.mjs";
import { checkGhAuth, listOpenIssues, validateIssue } from "./lib/github.mjs";
import { buildPrompt, assertPromptIsDataOnly } from "./lib/prompt.mjs";
import { runCline } from "./lib/runner.mjs";
import { createHealthReporter, readHealthFile } from "./lib/health.mjs";
import { createTriggerServer } from "./lib/webhook.mjs";

const SERVICE_NAME = "cline-task-watcher.service";
const SERVICE_UNIT_DIR = path.join(TOOL_ROOT, "systemd");

function parseArgs(argv) {
  const args = {
    config: null, dryRun: true, execute: false, once: false,
    intervalSec: 0, preflightOnly: false, installSystemd: false, uninstallSystemd: false,
    status: false, eventWebhook: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === "--config") args.config = argv[++i];
    else if (a === "--dry-run") { args.dryRun = true; args.execute = false; }
    else if (a === "--execute") { args.execute = true; args.dryRun = false; }
    else if (a === "--interval") { args.intervalSec = Number(argv[++i]) || 0; args.once = false; }
    else if (a === "--once") args.once = true;
    else if (a === "--preflight-only") args.preflightOnly = true;
    else if (a === "--status") args.status = true;
    else if (a === "--event-webhook") args.eventWebhook = true;
    else if (a === "--install-systemd") args.installSystemd = true;
    else if (a === "--uninstall-systemd") args.uninstallSystemd = true;
    else if (a === "--help" || a === "-h") args.help = true;
  }
  return args;
}

function printHelp() {
  process.stdout.write(`TASK-AUTOMATION-001/002 Cline task watcher

  --dry-run            (varsayılan) görevleri bul ve doğrula, Cline çalıştırma
  --execute            doğrulanmış görev için gerçek Cline CLI çalıştır
  --interval <sn>      fallback yoklama aralığı (görev hedefi 3–5 dk; 240 önerilir)
  --once               yalnız bir tur çalışıp çık (varsayılan: sürekli döngü)
  --event-webhook      yerel event alıcısını açar (secretEnv ortam değişkeninden)
  --preflight-only     yalnız ön kontroller (gh/cline/sürüm/dizin)
  --status             health/durum çıktısı (secret veya gövde içermez)
  --config <yol>       config.json yolu
  --install-systemd    systemd --user servisini kurar ve etkinleştirir
  --uninstall-systemd  servisi durdurur ve kaldırır
`);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Bir sonraki turu bekle: event gelirse anında, gelmezse `intervalSec` sonunda.
 *
 * Event modunda fallback bir ZAMAN AŞIMI olarak çalışır — yani event kaçırılırsa
 * (webhook kapalı, ağ hatası, relay yok) görev yine 3–5 dk içinde bulunur.
 *
 * `notifier` tek yazmalı bir kancadır: webhook ve graceful shutdown aynı kancayı
 * çağırır; ilk çağıran kazanır, tur bir kez tetiklenir.
 */
function waitForTrigger(intervalSec, notifier) {
  return new Promise((resolve) => {
    const finish = (sourceKind, eventType = null) => {
      clearTimeout(timer);
      if (notifier.value) notifier.value = null;
      resolve({ source: sourceKind, eventType });
    };
    const timer = setTimeout(() => finish("poll"), intervalSec * 1000);
    notifier.value = (eventType) => finish("event", eventType ?? null);
  });
}

/** PID hâlâ yaşıyor mu? (`--status` gözlemciliği için) */
function isAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (err) {
    return err?.code === "EPERM";
  }
}

function whichSync(bin) {
  const r = spawnSync("sh", ["-c", `command -v ${JSON.stringify(bin)}`], { encoding: "utf8" });
  const out = (r.stdout || "").trim();
  return out && existsSync(out) ? out : null;
}

function versionOf(bin, args) {
  try {
    return execFileSync(bin, args, { encoding: "utf8", timeout: 15000 }).trim().split("\n")[0];
  } catch {
    return "unknown";
  }
}

/** Ön kontroller: her şey doğrulanamazsa fail-closed. */
async function preflight(cfg, log) {
  const results = { ok: true, checks: {} };

  results.checks.repoPath = { ok: existsSync(cfg.repoPath), detail: cfg.repoPath };
  results.ok &&= results.checks.repoPath.ok;

  let clineBin = null;
  try {
    clineBin = resolveBin("cline", cfg, whichSync);
    results.checks.cline = { ok: true, path: clineBin, version: versionOf(clineBin, ["--version"]) };
  } catch (err) {
    results.checks.cline = { ok: false, detail: String(err.message) };
    results.ok = false;
  }

  let ghBin = null;
  try {
    ghBin = resolveBin("gh", cfg, whichSync);
    const auth = await checkGhAuth(ghBin, cfg.repo);
    results.checks.gh = { ok: auth.ok, path: ghBin, detail: auth.detail };
    results.ok &&= auth.ok;
  } catch (err) {
    results.checks.gh = { ok: false, detail: String(err.message) };
    results.ok = false;
  }

  log.info("preflight", {
    ok: results.ok,
    repo: cfg.repo,
    repoPathExists: results.checks.repoPath.ok,
    cline: results.checks.cline.version ?? "missing",
    ghAuth: results.checks.gh?.ok ?? false,
  });
  return { results, clineBin, ghBin };
}


/** Tek tur: keşif → doğrulama → duplicate → (opsiyonel) çalıştırma. */
export async function runOnce({ cfg, log, store, clineBin, ghBin, execute, health = null, onActiveCline = null }) {
  const issues = await listOpenIssues(ghBin, cfg.repo);
  log.info("issues_fetched", { count: issues.length });

  const candidates = [];
  for (const issue of issues) {
    const { eligible, reasons, taskId } = validateIssue(issue, cfg);
    if (!eligible) {
      log.info("issue_rejected", { number: issue.number, reasons });
      continue;
    }
    if (store.isDuplicate(taskId, issue.number)) {
      log.info("issue_duplicate_skipped", { number: issue.number, taskId });
      continue;
    }
    candidates.push({ issue, taskId });
  }

  if (candidates.length === 0) {
    log.info("no_actionable_task", {});
    return { status: "idle", candidates: 0 };
  }
  if (candidates.length > 1) {
    log.warn("multiple_actionable_tasks", {
      numbers: candidates.map((c) => c.issue.number),
      note: "only the first is executed (single active task rule)",
    });
  }

  const { issue, taskId } = candidates[0];
  const prompt = buildPrompt({ issue, taskId, cfg, stateNote: "first execution" });
  assertPromptIsDataOnly(prompt);

  store.upsert(taskId, issue.number, {
    status: "claimed", title: issue.title, url: issue.url,
    author: issue.author?.login ?? null,
  });
  log.info("task_claimed", { number: issue.number, taskId, title: issue.title });

  if (!execute) {
    store.upsert(taskId, issue.number, { status: "dry_run" });
    log.info("dry_run_complete", { number: issue.number, taskId, promptChars: prompt.length });
    return { status: "dry_run", taskId, issue: issue.number, promptChars: prompt.length };
  }

  const streamPath = path.join(cfg.logDir, `cline-${taskId}-${issue.number}.ndjson`);
  const startedAt = new Date().toISOString();
  store.upsert(taskId, issue.number, { status: "running", startedAt });
  health?.taskStarted({ taskId, issueNumber: issue.number, startedAt });

  const result = await runCline({
    clineBin, repoPath: cfg.repoPath, prompt,
    timeoutSec: cfg.timeoutSec, timeoutGraceSec: cfg.timeoutGraceSec,
    autoApprove: cfg.autoApprove === true,
    onStream: (kind, text) => log.clineStream(streamPath, `${kind === "stderr" ? "[stderr] " : ""}${text}`),
    // Graceful shutdown çalışan süreci güvenle sonlandırabilsin (req. 17).
    onSpawn: (abort) => onActiveCline?.(abort),
    onAbort: () => log.warn("cline_abort_requested", { number: issue.number, taskId }),
  });

  const runResult = result.runResult;
  store.upsert(taskId, issue.number, {
    status: result.outcome,
    finishedAt: new Date().toISOString(),
    durationMs: result.durationMs,
    exitCode: result.exitCode,
    finishReason: runResult?.finishReason ?? null,
    finishText: runResult?.text ? String(runResult.text).slice(0, 500) : null,
    usage: runResult?.usage ?? null,
    model: runResult?.model ?? null,
    streamLog: streamPath,
    messageCount: result.messageCount,
    timedOut: result.timedOut,
    aborted: result.aborted,
  });
  health?.taskFinished({ taskId, issueNumber: issue.number });
  onActiveCline?.(null);

  log.info("cline_finished", {
    taskId, number: issue.number, outcome: result.outcome,
    exitCode: result.exitCode, finishReason: runResult?.finishReason ?? null,
    durationMs: result.durationMs,
  });

  return {
    status: result.outcome, taskId, issue: issue.number,
    exitCode: result.exitCode, finishReason: runResult?.finishReason ?? null,
    text: runResult?.text ?? null, durationMs: result.durationMs,
    streamLog: streamPath,
  };
}



function systemdUnitText(cfg) {
  // Fallback yoklama aralığı: config değeri (varsayılan 240 sn = 4 dk hedefi).
  const parts = ["node", path.join(TOOL_ROOT, "watcher.mjs"),
    "--interval", String(cfg.fallbackIntervalSec), "--execute"];
  // Config dosyası varsa systemd unattended çalışmasında da kullanılır
  // (autoApprove / allowExecution burada tanımlıdır).
  const configPath = path.join(TOOL_ROOT, "config.json");
  if (existsSync(configPath)) parts.push("--config", configPath);
  else if (cfg.config) parts.push("--config", cfg.config);
  return `[Unit]
Description=LGS AI Coach GitHub -> Cline task watcher (TASK-AUTOMATION-001)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=${parts.join(" ")}
WorkingDirectory=${cfg.repoPath}
Restart=on-failure
RestartSec=30
KillSignal=SIGTERM
TimeoutStopSec=60
NoNewPrivileges=true
PrivateTmp=true
StandardOutput=append:${cfg.logDir}/systemd-stdout.log
StandardError=append:${cfg.logDir}/systemd-stderr.log

[Install]
WantedBy=default.target
`;
}

function installSystemd(cfg, log) {
  const targetDir = path.join(process.env.HOME ?? "", ".config", "systemd", "user");
  mkdirSync(targetDir, { recursive: true });
  copyFileSync(path.join(SERVICE_UNIT_DIR, SERVICE_NAME), path.join(targetDir, SERVICE_NAME));
  writeFileSync(path.join(SERVICE_UNIT_DIR, ".rendered"), systemdUnitText(cfg), "utf8");
  for (const argv of [["daemon-reload"], ["enable", "--now", SERVICE_NAME]]) {
    const r = spawnSync("systemctl", ["--user", ...argv], { encoding: "utf8" });
    log.info("systemd", { step: argv.join(" "), status: r.status });
    if (r.status !== 0) process.stderr.write(r.stderr || "");
  }
  log.info("systemd_installed", {});
}

function uninstallSystemd(log) {
  const unitPath = path.join(process.env.HOME ?? "", ".config", "systemd", "user", SERVICE_NAME);
  for (const argv of [["stop", SERVICE_NAME], ["disable", SERVICE_NAME]]) {
    spawnSync("systemctl", ["--user", ...argv], { encoding: "utf8" });
    log.info("systemd", { step: argv.join(" "), status: "done" });
  }
  spawnSync("rm", ["-f", unitPath], { encoding: "utf8" });
  spawnSync("systemctl", ["--user", "daemon-reload"], { encoding: "utf8" });
  log.info("systemd_removed", {});
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) return printHelp();

  const cfg = loadConfig(args.config);
  const log = createLogger({ logDir: cfg.logDir, dryRun: args.dryRun });
  const store = createStore(cfg.stateDir);

  if (args.installSystemd) return installSystemd(cfg, log);
  if (args.uninstallSystemd) return uninstallSystemd(log);

  // --status kilide bakmadan çalışır: gözlemcilik izleyicinin sağlığını
  // görmek için kullanılır, izleyicinin kendisi kilitliyken de çalışmalıdır.
  if (args.status) {
    const health = readHealthFile(cfg.stateDir);
    process.stdout.write(`${JSON.stringify({
      watcherRunning: health !== null && Boolean(health.pid) && isAlive(health.pid),
      lockPresent: existsSync(path.join(cfg.stateDir, "watcher.lock")),
      health,
      tasks: store.list().map((t) => ({
        taskId: t.taskId, issueNumber: t.issueNumber, status: t.status,
        startedAt: t.startedAt ?? null, finishedAt: t.finishedAt ?? null,
      })),
    }, null, 2)}\n`);
    return;
  }

  const lock = acquireLock(cfg.stateDir);
  if (!lock.acquired) {
    log.warn("another_watcher_running", { holderPid: lock.holder?.pid ?? null });
    process.stderr.write("FAIL CLOSED: başka bir watcher çalışıyor (tek instance kuralı).\n");
    process.exit(3);
  }
  log.info("lock_acquired", { pid: process.pid, stale: Boolean(lock.released) });

  // Yalnız kilidi doğruladıktan SONRA: ölü sahibin yarım kalan görevlerini
  // "interrupted" işaretle. (Kilit öncesi çağrılırsa ikinci bir instance
  // canlı görevin durumunu bozuyordu.)
  const reconciled = store.reconcileInterrupted();
  if (reconciled > 0) log.warn("interrupted_tasks_reconciled", { count: reconciled });

  let stopping = false;
  let activeClineAbort = null;
  let triggerServer = null;
  let health = null;
  /** Tek yazmalı uyandırma kancası: webhook ve graceful shutdown burayı çağırır. */
  const notifier = { value: null };

  /**
   * Graceful shutdown (TASK-AUTOMATION-002 gereksinimi 17).
   *
   * ÖNEMLİ: Kilit, çalışan Cline süreci gerçekten kapandıktan SONRA bırakılır.
   * Aksi halde ölmeyen bir Cline process'i devam ederken ikinci bir watcher
   * aynı görevi çalıştırabilir (duplicate ihlali).
   */
  const graceful = async (signal) => {
    if (stopping) return;
    stopping = true;
    log.warn("shutdown_signal", { signal, clineRunning: Boolean(activeClineAbort) });
    // Bekleyen turu hemen uyandır; döngü `stopping` görüp çıkar.
    notifier.value?.("shutdown");
    if (activeClineAbort) {
      try {
        activeClineAbort("shutdown");
        await sleep(2000);
      } catch { /* yok say */ }
    }
    health?.shutdown();
    releaseLock(lock);
    process.exit(0);
  };
  process.on("SIGTERM", () => void graceful("SIGTERM"));
  process.on("SIGINT", () => void graceful("SIGINT"));

  // Çalışan Cline sürecini izleyiciye bağla; görev bitince temizlenir.
  const onActiveCline = (abort) => { activeClineAbort = abort; };

  let triggerMode = "fallback";
  let round = 0;

  try {
    const { results, clineBin, ghBin } = await preflight(cfg, log);
    if (!results.ok) {
      log.error("preflight_failed", { checks: results.checks });
      process.stderr.write("FAIL CLOSED: ön kontroller başarısız.\n");
      process.exit(4);
    }
    if (args.preflightOnly) {
      process.stdout.write(`${JSON.stringify(results.checks, null, 2)}\n`);
      return;
    }

    // İki kapı: CLI bayrağı VE config anahtarı. İkisi de true olmalı.
    const execute = Boolean(args.execute) && cfg.allowExecution !== false;
    if (args.execute && !execute) {
      log.warn("execution_blocked_by_config", { allowExecution: false });
    }

    // Fallback yoklama aralığı: CLI > config > 240 sn (3–5 dk hedefi).
    const intervalSec = args.intervalSec > 0 ? args.intervalSec : cfg.fallbackIntervalSec;
    if (args.intervalSec > 0 && args.intervalSec < cfg.minPollIntervalSec) {
      log.warn("interval_clamped", { requested: args.intervalSec, applied: cfg.minPollIntervalSec });
    }

    // Event-driven alıcı (tercih edilen tetikleme).
    const wantEvents = args.eventWebhook || cfg.eventWebhook?.enabled === true;
    if (wantEvents) {
      const secretEnv = cfg.eventWebhook?.secretEnv ?? "CLINE_WATCHER_WEBHOOK_SECRET";
      const secret = process.env[secretEnv];
      if (!secret) {
        // Fail-closed: secret yoksa event yolu devreye girmez, fallback çalışır.
        log.error("event_secret_missing", { secretEnv });
      } else {
        triggerServer = createTriggerServer({
          secret,
          host: cfg.eventWebhook.host,
          port: cfg.eventWebhook.port,
          path: cfg.eventWebhook.path,
          maxBodyBytes: cfg.eventWebhook.maxBodyBytes,
          onTrigger: ({ event }) => notifier.value?.(event),
          onLog: (event, data) => log.warn(`event_${event}`, data),
        });
        try {
          const { port } = await triggerServer.start();
          triggerMode = "event+fallback";
          log.info("event_listener_started", {
            host: cfg.eventWebhook.host, port, path: cfg.eventWebhook.path,
          });
        } catch (err) {
          // Event açılamazsa servis ölmez; fallback polling geçerli olur.
          log.error("event_listener_failed", { detail: String(err?.message ?? err).slice(0, 200) });
          triggerServer = null;
        }
      }
    }

    health = createHealthReporter({ stateDir: cfg.stateDir, intervalSec, triggerMode });
    health.flush();
    log.info("watcher_started", {
      pid: process.pid, execute, intervalSec, triggerMode, repo: cfg.repo,
    });

    /**
     * Sürekli döngü (TASK-AUTOMATION-002):
     *  - event gelirse anında, gelmezse `intervalSec` (240 sn) sonunda tarama;
     *  - tur hatası servisi düşürmez, backoff ile sonraki turda devam eder (req. 9);
     *  - görev yoksa/atlanırsa çıkılmaz, bekleme durumuna dönülür (req. 8);
     *  - tur tur seri çalışır: aynı anda tek Cline süreci (req. 15).
     */
    for (;;) {
      if (stopping) break;
      // İlk tur beklemeden yapılır; sonrakiler event/fallback ile bekler.
      const trigger = round === 0 ? { source: "poll", eventType: null } : await waitForTrigger(intervalSec, notifier);
      if (stopping) break;
      round += 1;
      health.roundStart({ source: trigger.source, eventType: trigger.eventType });
      try {
        const outcome = await runOnce({ cfg, log, store, clineBin, ghBin, execute, health, onActiveCline });
        process.stdout.write(`${JSON.stringify(outcome, null, 2)}\n`);
        health.roundFinished({ status: "ok" });
      } catch (err) {
        const detail = String(err?.message ?? err).slice(0, 300);
        log.error("round_failed", { detail });
        health.roundFinished({ status: "error", error: detail });
        // Servisi düşürmeden, API'yi yormadan sonraki turda devam et.
        await sleep(Math.min(intervalSec, 30) * 1000);
      }
      // Yalnız `--once` ile TEK tur çalış; aksi halde sürekli döngü (sistemd).
      if (args.once && !args.intervalSec && !wantEvents) break;
    }
  } catch (err) {
    log.error("watcher_error", { detail: String(err?.message ?? err).slice(0, 300) });
    process.stderr.write(`HATA: ${String(err?.message ?? err)}\n`);
    process.exit(5);
  } finally {
    if (triggerServer) await triggerServer.close();
    releaseLock(lock);
  }
}

// Yalnız doğrudan çalıştırıldığında main() tetiklenir; testler modülü içe aktarabilir.
const isDirectRun = process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url;
if (isDirectRun) {
  main().catch((err) => {
    process.stderr.write(`FATAL: ${String(err?.message ?? err)}\n`);
    process.exit(6);
  });
}

export { main as runMain };

