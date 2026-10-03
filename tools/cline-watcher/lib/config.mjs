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
   * true: Product Owner tarafından 2026-10-02'de açıkça onaylandı.
   *   Cline 3.0.62 headless oturumda onay gerektiren araçları
   *   "tool approval requires an interactive session" ile reddettiği için
   *   unattended (insansız) çalışmada bu değer true olmalıdır.
   */
  autoApprove: true,
  /** Cline süreç zaman aşımı (saniye) + izleyici için ek tolerans. */
  timeoutSec: 1800,
  timeoutGraceSec: 90,
  /** Durum ve günlük dizinleri. */
  stateDir: path.join(TOOL_ROOT, "state"),
  logDir: path.join(TOOL_ROOT, "logs"),
  /** Varsayılan: yalnızca tespit + doğrula, Cline çalıştırma. */
  dryRun: true,
  /**
   * Yapılandırma düzeyinde ana çalıştırma anahtarı.
   *
   * Çalıştırma için İKİ koşul gerekir: `--execute` bayrağı VE `allowExecution: true`.
   * Bu değer `false` yapılırsa systemd unattended çalışması da durur
   * (ikinci güvenlik kapısı / acil durum freni).
   */
  allowExecution: true,
  /** Cline ve gh için aranacak konumlar (PATH dışı kurulumlar için). */
  binCandidates: {
    cline: ["cline", "/usr/local/bin/cline"],
    gh: ["gh", "/home/selam/.local/gh-cli/gh_2.102.0_linux_amd64/bin/gh"],
  },
  /**
   * Event-driven tetikleme (tercih edilen yol).
   *
   * GitHub webhook'i genel bir URL'ye teslim edilir; yerel alıcı yalnız 127.0.0.1
   * dinler ve isteği HMAC-SHA256 imzasıyla doğrular. `secretEnv` bir DEĞİŞKEN
   * ADIDIR — değeri repo'ya, state'e veya loga asla yazılmaz.
   *
   * Kapı NOTU: webhook'un ulaşabilmesi için genel erişilebilir bir relay/tunnel
   * gerekir; bu bir altyapı/ürün kararıdır (bkz. handoff PENDING).
   * Devre dışı bırakılırsa `fallbackIntervalSec` polling'i geçerli olur.
   */
  eventWebhook: {
    enabled: false,
    host: "127.0.0.1",
    port: 8787,
    path: "/cline-trigger",
    /** İmza doğrulaması için ortam değişkeni ADI (değer burada tutulmaz). */
    secretEnv: "CLINE_WATCHER_WEBHOOK_SECRET",
    /** İstek gövdesi üst sınırı (bayt) — bellek/DoS koruması. */
    maxBodyBytes: 64 * 1024,
  },
  /**
   * Fallback yoklama aralığı (saniye).
   *
   * Görev hedefi 3–5 dakikadır. Seçilen değer **240 sn (4 dk)**: 5 dk sınırının
   * altında kalır, 3 dk'nın üstünde olup GitHub API yükünü ikiye katlamaz.
   * Event-driven etkinse bu değer yalnız event kaçırıldığında/üretilemediğinde
   * devreye girer.
   */
  fallbackIntervalSec: 240,
  /** Fallback aralığının alt sınırı (yanlışlıkla API'ye yüklenmeyi önler). */
  minPollIntervalSec: 60,
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
  // eventWebhook yarı yapılandırılmışsa fail-closed (sessizce devre dışı kalmasın).
  if (cfg.eventWebhook && typeof cfg.eventWebhook !== "object") {
    throw new Error("eventWebhook bir nesne olmalı");
  }
  // Aşırı sık yoklama (rate-limit) kendini korur: alt sınır uygulanır.
  if (cfg.fallbackIntervalSec < cfg.minPollIntervalSec) {
    cfg.fallbackIntervalSec = cfg.minPollIntervalSec;
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
