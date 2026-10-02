/**
 * Watcher yapılandırması.
 *
 * Güvenlik notu: `repo`, `repoPath` ve `trustedAuthors` yalnızca bu dosyadan
 * gelir. Issue gövdesinden veya CLI argümanından asla değiştirilemez.
 */
import { readFileSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const TOOL_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export const DEFAULTS = {
  /** Yetkili tek depo. Fail-closed: eşleşmezse hiçbir görev çalıştırılmaz. */
  repo: "abektas/lgs-ai-coach",
  /** Çalışma dizini (Cline --cwd). */
  repoPath: path.join(homedir(), "roller", "web", "lgs-ai-coach"),
  /** Görev yazabilen güvenilir GitHub hesapları. */
  trustedAuthors: ["abektas"],
  /** Gövdede bulunması gereken hazır durum işareti. */
  readyStatus: "READY_FOR_CLINE",
  /** Gövdede bulunması zorunlu yapısal alanlar (Issue #1 sözleşmesi). */
  requiredMarkers: [
    "**Task ID:**",
    "**Agent:**",
    "**Status:**",
    "## Objective",
    "## Scope",
  ],
  /** Issue #1: "Agent: Cline" zorunlu. */
  requiredAgent: "Cline",
  /** Etiket bazlı yetkilendirme açıksa (labels yoksa gövde işareti kullanılır). */
  requiredLabel: null,
  /**
   * Cline `--auto-approve` değeri.
   *
   * Varsayılan `false` (fail-safe). ÖNEMLİ: Cline 3.0.62 headless oturumda
   * onay gerektiren araçları reddeder ("Tool approval requires an interactive
   * session"), yani `false` ile görev hiçbir iş yapmadan no-op biter.
   * Gerçek unattended çalıştırma için `true` gerekir; bu bir güvenlik
   * kararıdır ve Product Owner onayı gerektirir.
   */
  autoApprove: false,
  /** Cline süreç zaman aşımı (saniye) + izleyici için ek tolerans. */
  timeoutSec: 1800,
  timeoutGraceSec: 90,
  /** Durum ve günlük dizinleri. */
  stateDir: path.join(TOOL_ROOT, "state"),
  logDir: path.join(TOOL_ROOT, "logs"),
  /** Varsayılan: yalnızca tespit + doğrula, Cline çalıştırma. */
  dryRun: true,
  /** Cline çalıştırmaya izin ver (güvenlik kapısı; --execute ile de açılabilir). */
  allowExecution: false,
  /** Cline ve gh için aranacak konumlar (PATH dışı kurulumlar için). */
  binCandidates: {
    cline: ["cline", "/usr/local/bin/cline"],
    gh: ["gh", "/home/selam/.local/gh-cli/gh_2.102.0_linux_amd64/bin/gh"],
  },
};

/** Yapılandırmayı yükler; JSON dosyası verilmezse güvenli varsayılanlar. */
export function loadConfig(configPath) {
  let user = {};
  if (configPath) {
    if (!existsSync(configPath)) throw new Error(`config dosyası yok: ${configPath}`);
    user = JSON.parse(readFileSync(configPath, "utf8"));
  }
  const cfg = { ...DEFAULTS, ...user };
  // stateDir/logDir göreli verilirse araç köküne göre çözülür.
  for (const key of ["stateDir", "logDir", "repoPath"]) {
    if (typeof cfg[key] === "string" && !path.isAbsolute(cfg[key])) {
      cfg[key] = path.resolve(TOOL_ROOT, cfg[key]);
    }
  }
  if (!Array.isArray(cfg.trustedAuthors) || cfg.trustedAuthors.length === 0) {
    throw new Error("trustedAuthors boş olamaz (fail-closed)");
  }
  if (!cfg.repo || !cfg.repo.includes("/")) {
    throw new Error("repo 'owner/name' biçiminde olmalı");
  }
  return cfg;
}

/** Kurulu binari bulur (PATH yoksa aday konumlara bakar). */
export function resolveBin(name, cfg, which) {
  for (const candidate of cfg.binCandidates[name] ?? [name]) {
    const found = which(candidate);
    if (found) return found;
  }
  throw new Error(`${name} bulunamadı (PATH ve ${cfg.binCandidates[name]?.join(", ")})`);
}
