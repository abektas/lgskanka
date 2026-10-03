/**
 * GitHub görev keşfi ve yetkilendirme doğrulaması.
 *
 * Kimlik: mevcut `gh auth` (token hard-code edilmez).
 * Güvenlik:
 *  - depo yalnız config'den (SABİT "abektas/lgs-ai-coach")
 *  - tüm alt süreçler argüman dizisiyle (shell YOK)
 *  - her koşul sağlanmazsa görev reddedilir (fail-closed)
 */
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const exec = promisify(execFile);

/** gh mevcut mu ve oturum açık mı? */
export async function checkGhAuth(ghBin, repo) {
  try {
    const { stdout } = await exec(ghBin, ["auth", "status"], { timeout: 20000 });
    return { ok: true, detail: stdout.split("\n")[0] ?? "" };
  } catch (err) {
    return { ok: false, detail: String(err?.stderr || err?.message || "auth status failed").slice(0, 200) };
  }
}

/**
 * Depodaki açık issue'ları çeker (yalnız config deposu).
 *
 * Hız sınırı notu: `fallbackIntervalSec` (240 sn) tek bir `gh issue list`
 * çağrısı demektir ≈ 15 istek/saat; GitHub'ın saatlik limitinin çok altında.
 * Uydurma bir ETag/koşullu istek mekanizması KULLANILMAZ — `gh` CLI'da
 * doğrulanmış karşılığı yoktur.
 */
export async function listOpenIssues(ghBin, repo) {
  const { stdout } = await exec(
    ghBin,
    ["issue", "list", "--repo", repo, "--state", "open", "--limit", "50",
      "--json", "number,title,body,author,labels,state,url,createdAt"],
    { timeout: 60000, maxBuffer: 8 * 1024 * 1024 },
  );
  const parsed = JSON.parse(stdout || "[]");
  return Array.isArray(parsed) ? parsed : [];
}

const TASK_ID_RE = /^TASK-[A-Z0-9]+-\d+$/;

/** Gövdeden Task ID (markdown kalın biçimlendirmeli). */
export function parseTaskId(body) {
  const match = String(body ?? "").match(/\*\*Task ID:\*\*\s*`?([A-Za-z0-9_-]+)`?/);
  return match ? match[1].trim() : null;
}

function labelNames(issue) {
  return (issue.labels ?? []).map((l) => (typeof l === "string" ? l : l?.name)).filter(Boolean);
}

/**
 * Tek bir issue için yetkilendirme kapıları.
 * @returns {{eligible:boolean, reasons:string[], taskId:string|null}}
 */
export function validateIssue(issue, cfg) {
  const reasons = [];
  const body = String(issue?.body ?? "");
  const author = issue?.author?.login;

  // 1) Depo kimliği (config'ten; issue'tan gelen hiçbir değere güvenilmez)
  if (!cfg.repo || cfg.repo !== "abektas/lgs-ai-coach") {
    reasons.push("repository_not_allowed");
  }
  // 2) Açık issue
  if (issue?.state !== "OPEN") reasons.push("issue_not_open");
  // 3) Güvenilir yazar
  if (!author || !cfg.trustedAuthors.includes(author)) {
    reasons.push("untrusted_author");
  }
  // 4) Hazır işareti: gövdede Status + Agent (etiket varsa ek kapı)
  const statusReady = new RegExp(`\\*\\*Status:\\*\\*\\s*\`?${cfg.readyStatus}\`?`, "i").test(body);
  const agentOk = new RegExp(`\\*\\*Agent:\\*\\*\\s*\`?${cfg.requiredAgent}\`?`, "i").test(body);
  if (!statusReady) reasons.push("not_marked_ready");
  if (!agentOk) reasons.push("agent_not_cline");
  if (cfg.requiredLabel && !labelNames(issue).includes(cfg.requiredLabel)) {
    reasons.push("missing_required_label");
  }
  // 5) Yapısal zorunluluklar.
  for (const marker of cfg.requiredMarkers) {
    if (!body.includes(marker)) reasons.push(`missing_marker:${marker}`);
  }

  // 5b) Kademeli şablon kontrolü: gövde şablona ozgu bir bolum basligi
  // iceriyorsa "yeni bicim" sayilir ve tum ek alanlar zorunlu olur.
  // Boylece yeni sablonu takip eden gorevler dogrulanir, eski bicimli
  // gorevler reddedilmez.
  const templateMarkers = cfg.templateMarkers ?? [];
  const templateTriggers = cfg.templateTriggers ?? templateMarkers;
  if (templateMarkers.length > 0 && templateTriggers.some((m) => body.includes(m))) {
    for (const marker of templateMarkers) {
      if (!body.includes(marker)) reasons.push(`missing_marker:${marker}`);
    }
  }
  const taskId = parseTaskId(body);
  if (!taskId || !TASK_ID_RE.test(taskId)) reasons.push("invalid_task_id");

  return { eligible: reasons.length === 0, reasons, taskId };
}
