#!/usr/bin/env node
/**
 * TASK-AUTOMATION-001 — GitHub → Cline CLI task watcher/runner.
 *
 * Akış: GitHub Issue → keşif → yetkilendirme → duplicate → güvenli prompt →
 *       Cline CLI headless → NDJSON/run_result → kalıcı state/log.
 *
 * Güvenlik varsayılanları: dry-run AÇIK, Cline `--auto-approve false`, tek instance,
 * gövde asla komut olarak çalıştırılmaz, doğrulama başarısızsa FAIL CLOSED.
 *
 * Kullanım:
 *   node tools/cline-watcher/watcher.mjs --dry-run
 *   node tools/cline-watcher/watcher.mjs --execute
 *   node tools/cline-watcher/watcher.mjs --interval 300
 *   node tools/cline-watcher/watcher.mjs --preflight-only
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

const SERVICE_NAME = "cline-task-watcher.service";
const SERVICE_UNIT_DIR = path.join(TOOL_ROOT, "systemd");

function parseArgs(argv) {
  const args = {
    config: null, dryRun: true, execute: false, once: true,
    intervalSec: 0, preflightOnly: false, installSystemd: false, uninstallSystemd: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === "--config") args.config = argv[++i];
    else if (a === "--dry-run") { args.dryRun = true; args.execute = false; }
    else if (a === "--execute") { args.execute = true; args.dryRun = false; }
    else if (a === "--interval") { args.intervalSec = Number(argv[++i]) || 0; args.once = false; }
    else if (a === "--preflight-only") args.preflightOnly = true;
    else if (a === "--install-systemd") args.installSystemd = true;
    else if (a === "--uninstall-systemd") args.uninstallSystemd = true;
    else if (a === "--help" || a === "-h") args.help = true;
  }
  return args;
}

function printHelp() {
  process.stdout.write(`TASK-AUTOMATION-001 Cline task watcher

  --dry-run            (varsayılan) görevleri bul ve doğrula, Cline çalıştırma
  --execute            doğrulanmış görev için gerçek Cline CLI çalıştır
  --interval <sn>      sürekli tekrar (sistemd altında)
  --preflight-only     yalnız ön kontroller (gh/cline/sürüm/dizin)
  --config <yol>       config.json yolu
  --install-systemd    systemd --user servisini kurar ve etkinleştirir
  --uninstall-systemd  servisi durdurur ve kaldırır
`);
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
export async function runOnce({ cfg, log, store, clineBin, ghBin, execute }) {
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
  store.upsert(taskId, issue.number, { status: "running", startedAt: new Date().toISOString() });

  const result = await runCline({
    clineBin, repoPath: cfg.repoPath, prompt,
    timeoutSec: cfg.timeoutSec, timeoutGraceSec: cfg.timeoutGraceSec,
    autoApprove: cfg.autoApprove === true,
    onStream: (kind, text) => log.clineStream(streamPath, `${kind === "stderr" ? "[stderr] " : ""}${text}`),
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
  });

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
  const parts = ["node", path.join(TOOL_ROOT, "watcher.mjs"), "--interval", "300", "--execute"];
  if (cfg.config) parts.push("--config", cfg.config);
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
  store.reconcileInterrupted();

  if (args.installSystemd) return installSystemd(cfg, log);
  if (args.uninstallSystemd) return uninstallSystemd(log);

  const lock = acquireLock(cfg.stateDir);
  if (!lock.acquired) {
    log.warn("another_watcher_running", { holderPid: lock.holder?.pid ?? null });
    process.stderr.write("FAIL CLOSED: başka bir watcher çalışıyor (tek instance kuralı).\n");
    process.exit(3);
  }
  log.info("lock_acquired", { pid: process.pid, stale: Boolean(lock.released) });

  let stopping = false;
  const graceful = (signal) => {
    if (stopping) return;
    stopping = true;
    log.warn("shutdown_signal", { signal });
    releaseLock(lock);
    process.exit(0);
  };
  process.on("SIGTERM", () => graceful("SIGTERM"));
  process.on("SIGINT", () => graceful("SIGINT"));

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
    do {
      const outcome = await runOnce({ cfg, log, store, clineBin, ghBin, execute });
      process.stdout.write(`${JSON.stringify(outcome, null, 2)}\n`);
      if (!args.intervalSec) break;
      await new Promise((r) => setTimeout(r, args.intervalSec * 1000));
    } while (!stopping);
  } catch (err) {
    log.error("watcher_error", { detail: String(err?.message ?? err).slice(0, 300) });
    process.stderr.write(`HATA: ${String(err?.message ?? err)}\n`);
    process.exit(5);
  } finally {
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

