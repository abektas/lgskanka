/**
 * Test yardımcıları: sahte `gh` ve `cline` binleri + issue fixture'ları.
 *
 * Testler ASLA gerçek ağa çıkmaz, gerçek Cline çağırmaz ve gerçek repo'ya yazmaz.
 */
import { existsSync, mkdirSync, writeFileSync, chmodSync, copyFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { DEFAULTS } from "../lib/config.mjs";

export const VALID_BODY = [
  "# TASK",
  "",
  "**Task ID:** `TASK-AUTOMATION-001`",
  "**Agent:** Cline",
  "**Status:** `READY_FOR_CLINE`",
  "**Priority:** P1",
  "",
  "## Objective",
  "Do the thing.",
  "",
  "## Scope",
  "- in scope",
].join("\n");

export function makeIssue(overrides = {}) {
  return {
    number: 1,
    title: "[TASK] Example",
    state: "OPEN",
    url: "https://github.com/abektas/lgs-ai-coach/issues/1",
    author: { login: "abektas" },
    labels: [],
    createdAt: "2026-10-02T00:00:00Z",
    body: VALID_BODY,
    ...overrides,
  };
}

/** Geçici dizinde sahte binler üretir; PATH öneki döndürür. */
export function makeStubBin({ issues = [], clineMode = "success", clineSleepMs = 0, recordFile } = {}) {
  const dir = mkdtempSync(path.join(tmpdir(), "cw-test-"));
  const bin = path.join(dir, "bin");
  mkdirSync(bin, { recursive: true });
  const issuesFile = path.join(dir, "issues.json");
  writeFileSync(issuesFile, JSON.stringify(issues));
  const recordTarget = recordFile ?? path.join(dir, "cline-args.json");

  const gh = `#!/usr/bin/env node
const fs = require("fs");
const args = process.argv.slice(2);
if (args[0] === "auth") { console.log("stub gh: logged in"); process.exit(0); }
if (args[0] === "issue" && args[1] === "list") {
  process.stdout.write(fs.readFileSync(${JSON.stringify(issuesFile)}, "utf8"));
  process.exit(0);
}
process.stderr.write("stub gh: unsupported\\n");
process.exit(9);
`;
  writeFileSync(path.join(bin, "gh"), gh);
  chmodSync(path.join(bin, "gh"), 0o755);

  const cline = `#!/usr/bin/env node
const fs = require("fs");
const args = process.argv.slice(2);
if (args.includes("--version")) { console.log("cline-stub 3.0.62"); process.exit(0); }
const record = { args, cwd: process.cwd(), argvHasShell: false };
fs.writeFileSync(${JSON.stringify(recordTarget)}, JSON.stringify(record, null, 2));
const mode = ${JSON.stringify(clineMode)};
const sleep = ${clineSleepMs};
function emit(o) { process.stdout.write(JSON.stringify(o) + "\\n"); }
setTimeout(() => {
  emit({ type: "agent_event", event: { type: "done", reason: "completed", text: "STUB_OK", iterations: 1, usage: { inputTokens: 10, outputTokens: 2, totalCost: 0 } } });
  if (mode === "success") {
    emit({ type: "run_result", finishReason: "completed", iterations: 1, durationMs: 5, text: "STUB_OK", usage: { inputTokens: 10, outputTokens: 2, totalCost: 0 }, model: { id: "stub-model", provider: "stub" } });
    process.exit(0);
  }
  if (mode === "no_result") { process.exit(0); }
  if (mode === "failure") { process.stderr.write("stub cline failure\\n"); process.exit(1); }
  process.exit(0);
}, sleep);
`;
  writeFileSync(path.join(bin, "cline"), cline);
  chmodSync(path.join(bin, "cline"), 0o755);

  return { dir, bin, issuesFile, recordFile };
}

/** Testler için geçici çalışma dizini (sahte repo). */
export function makeFakeRepo() {
  return mkdtempSync(path.join(tmpdir(), "cw-repo-"));
}

/** Test config'i üretir (güvenli varsayılanlarla birleştirilir). */
export function makeConfig(overrides = {}) {
  const root = mkdtempSync(path.join(tmpdir(), "cw-cfg-"));
  return {
    ...DEFAULTS,
    repoPath: makeFakeRepo(),
    stateDir: path.join(root, "state"),
    logDir: path.join(root, "logs"),
    binCandidates: { cline: ["cline"], gh: ["gh"] },
    timeoutSec: 5,
    timeoutGraceSec: 1,
    ...overrides,
    __root: root,
  };
}
