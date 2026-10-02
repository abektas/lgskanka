/**
 * Cline CLI headless çalıştırıcı.
 *
 * Doğrulanmış komut biçimi (Cline 3.0.62, `cline --help`):
 *   cline --json --auto-approve false --timeout <sn> --cwd <path> "<prompt>"
 *
 * - spawn argüman DİZİSİ ile çağrılır → shell yok, shell enjeksiyonu imkânsız.
 * - NDJSON satırları ayrıştırılır; final `run_result` saklanır.
 * - İki zaman aşımı: Cline'ın kendi `--timeout` değeri + izleyicinin sert watchdog'u.
 */
import { spawn } from "node:child_process";

export const CLINE_ARGS = (repoPath, timeoutSec, autoApprove = false) => [
  "--json",
  "--auto-approve", String(autoApprove),
  "--timeout", String(timeoutSec),
  "--cwd", repoPath,
];

function parseNdjson(text) {
  const messages = [];
  const errors = [];
  for (const line of String(text).split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || !trimmed.startsWith("{")) continue;
    try {
      messages.push(JSON.parse(trimmed));
    } catch {
      errors.push("unparsable_ndjson_line");
    }
  }
  return { messages, errors };
}

/**
 * @returns {Promise<{outcome:string, exitCode:number|null, runResult:object|null,
 *                    messageCount:number, stdout:string, stderr:string, timedOut:boolean}>}
 */
export function runCline({ clineBin, repoPath, prompt, timeoutSec, timeoutGraceSec = 90, autoApprove = false, onStream }) {
  const args = [...CLINE_ARGS(repoPath, timeoutSec, autoApprove), prompt];
  const startedAt = Date.now();
  return new Promise((resolve) => {
    const child = spawn(clineBin, args, {
      cwd: repoPath,
      env: { ...process.env, NO_COLOR: "1" },
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    let timedOut = false;
    let settled = false;

    const watchdog = setTimeout(() => {
      timedOut = true;
      try {
        child.kill("SIGTERM");
        setTimeout(() => child.kill("SIGKILL"), 10_000).unref?.();
      } catch {
        /* yok say */
      }
    }, (timeoutSec + timeoutGraceSec) * 1000);

    child.stdout.on("data", (chunk) => {
      const text = chunk.toString();
      stdout += text;
      onStream?.("stdout", text);
    });
    child.stderr.on("data", (chunk) => {
      const text = chunk.toString();
      stderr += text;
      onStream?.("stderr", text);
    });

    const finish = (exitCode, signal) => {
      if (settled) return;
      settled = true;
      clearTimeout(watchdog);
      const { messages, errors } = parseNdjson(stdout);
      const runResult =
        [...messages].reverse().find((m) => m.type === "run_result") ?? null;
      const done = [...messages].reverse().find((m) => m?.event?.type === "done") ?? null;

      let outcome;
      if (timedOut) {
        outcome = "timeout";
      } else if (exitCode === 0 && runResult?.finishReason === "completed") {
        outcome = "succeeded";
      } else if (exitCode === 0 && !runResult) {
        outcome = "failed"; // çıktı yok: kanıt eksik → başarı sayma
      } else if (runResult?.finishReason === "aborted") {
        outcome = "timeout"; // Cline'ın kendi --timeout'u (farklı çıkış kodu)
      } else {
        outcome = "failed";
      }

      resolve({
        outcome,
        exitCode: exitCode ?? null,
        signal: signal ?? null,
        runResult,
        doneEvent: done,
        messageCount: messages.length,
        parseErrors: errors,
        stdout,
        stderr,
        timedOut,
        durationMs: Date.now() - startedAt,
        command: `${clineBin} --json --auto-approve false --timeout ${timeoutSec} --cwd ${repoPath} "<prompt>"`,
      });
    };

    child.on("error", (err) => {
      stderr += String(err?.message ?? err);
      finish(null, null);
    });
    child.on("close", (code, signal) => finish(code, signal));
  });
}
