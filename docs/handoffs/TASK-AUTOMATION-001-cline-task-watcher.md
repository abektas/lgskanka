# TASK-AUTOMATION-001 — GitHub → Cline Task Watcher · Handoff

**Tarih:** 2026-10-02 · **Issue:** #1 · **Branch:** `task/TASK-AUTOMATION-001-cline-watcher`
**Mekanizma:** Cline CLI headless (`--json`). **SDK kullanılmadı, entegrasyonu yapılmadı.**

---

## 1. Yapılanlar

- `tools/cline-watcher/` altında **sıfır bağımlılıklı** Node.js watcher/runner (yalnız Node 22 standart kütüphanesi).
- Akış: GitHub Issue → `gh` ile keşif → yetkilendirme kapıları → duplicate kontrolü → güvenli prompt → Cline CLI headless → NDJSON/`run_result` ayrıştırma → kalıcı state + yapılandırılmış log.
- 14 senaryoluk test paketi (`npm run test:watcher`) — stub `gh`/`cline` ile, **gerçek ağ/Cline kullanmadan**.
- systemd user-service unit + `--install-systemd` / `--uninstall-systemd` komutları.
- Dokümantasyon: `tools/cline-watcher/README.md` (kurulum, kullanım, dry-run, test, systemd, durdurma, kaldırma, rollback).

## 2. Dosyalar

| Dosya | Rol |
|---|---|
| `tools/cline-watcher/watcher.mjs` | CLI girişi: preflight, keşif, doğrulama, çalıştırma, lock, graceful shutdown, systemd yönetimi |
| `tools/cline-watcher/lib/config.mjs` | Güvenli varsayılanlar + config yükleme + bin çözümleme |
| `tools/cline-watcher/lib/github.mjs` | `gh auth` kontrolü, açık issue listeleme, **yetkilendirme kapıları** (fail-closed) |
| `tools/cline-watcher/lib/prompt.mjs` | Güvenli prompt üretimi; gövde `<<<UNTRUSTED_TASK_CONTENT …>>>` bloğunda |
| `tools/cline-watcher/lib/runner.mjs` | Cline spawn (argüman dizisi, shell yok), NDJSON parse, timeout, sonuç sınıflandırma |
| `tools/cline-watcher/lib/state.mjs` | Atomik kalıcı state, duplicate kontrolü, restart sonrası `interrupted` işaretleme |
| `tools/cline-watcher/lib/lock.mjs` | Tek-instance kilidi (O_EXCL, stale PID devralma) |
| `tools/cline-watcher/lib/log.mjs` | Redakte eden yapılandırılmış log (0600), Cline NDJSON akış dosyası |
| `tools/cline-watcher/test/{watcher.test.mjs,helpers.mjs}` | 14 senaryo + stub bin/issue fixture'ları |
| `tools/cline-watcher/{README.md,config.example.json}` | Dokümantasyon + örnek config (token içermez) |
| `tools/cline-watcher/systemd/cline-task-watcher.service` | systemd user unit şablonu |
| `package.json` | `test:watcher` script'i eklendi |
| `.gitignore` | `state/`, `logs/`, `config.json`, `systemd/.rendered` eklendi |

## 3. Gerçek Cline CLI komutu / entegrasyonu

Kurulu Cline **3.0.62**; `cline --help` ile doğrulanan bayraklar kullanıldı (tahmin yok):

```
cline --json --auto-approve <true|false> --timeout <sn> --cwd <repoPath> "<prompt>"
```

- `spawn(clineBin, args)` — **argüman dizisi**, `shell:false` → shell enjeksiyonu imkânsız.
- Otomatik olarak `--json`, `--timeout`, `--cwd`; `--auto-approve` config'den.
- `--auto-approve` varsayılanı `true`'dur (Product Owner kararı, 2026-10-02, commit `987ffe0`).

## 4. Dry-run sonucu ✅

```
node tools/cline-watcher/watcher.mjs --preflight-only
  → repoPath ✓ · cline 3.0.62 (/usr/local/bin/cline) · gh auth ✓ (keyring)

node tools/cline-watcher/watcher.mjs --dry-run
  → issues_fetched count=1
  → task_claimed number=1 taskId=TASK-AUTOMATION-001
  → dry_run_complete promptChars=6436
  → state: TASK-AUTOMATION-001#1 = dry_run
```
Gerçek GitHub, gerek Issue #1, **Cline çalıştırılmadı**. Aynı komut tekrar çalıştırıldığında `issue_duplicate_skipped` + `no_actionable_task` → **duplicate koruması gerçek ortamda doğrulandı**.

## 5. Gerçek tek-task test sonucu (2 koşu)

Çalışma ağacını korumak için **sandbox kopyada** (`/tmp/nuli-sandbox`) çalıştırıldı; canlı çalışma ağacı hiç değişmedi (`git status` temiz kaldı).

| Koşu | `autoApprove` | Sonuç | Kanıt |
|---|---|---|---|
| 1 | `false` | `succeeded`, exit 0, completed, 26 sn | Model çıktısı: **"Blocked: no tools are available in this session — Tool approval requires an interactive session, but this session is non-interactive."** |
| 2 | `true` | `timeout`, exit 1, `finishReason=aborted`, 429 sn | Cline gerçekten çalıştı (iteration 17, sandbox'ta `tsc` koştu), sonra `--timeout 420` sınırına takıldı |

### Çözülen karar (2026-10-02) — `autoApprove: true`

~~⚠️ **OWNER_DECISION_REQUIRED:**~~ → **KARAR VERİLDİ.** Product Owner `autoApprove: true`'yu
onayladı; varsayılan ve `config.example.json` buna göre güncellendi (commit `987ffe0`).
Ayrıca `allowExecution` ikinci kapı olarak **gerçek bir config anahtarına** dönüştürüldü
(`--execute` **VE** `allowExecution: true` gerekir) → acil durum freni.

Bu, unattended çalıştırmada **tam araç yetkisi** demektir. Kapsamı daraltmak için
`CLINE_COMMAND_PERMISSIONS` kullanılabilir. Servis hâlâ `disabled` bırakıldı.

## 6. Test sonuçları

| Komut | Sonuç |
|---|---|
| `npm run test:watcher` | ✅ **14/14** (11 zorunlu senaryo + "run_result yoksa başarı sayılmaz" + `allowExecution` kapısı + PO varsayılanları) |
| `npm run test:source` | ✅ 83 Python OK + 3 node OK |
| `npm run test:ai` | ✅ 19/19 |
| `npm run test:taxonomy` | ✅ 5/5 |
| `npx tsc --noEmit` | ✅ 0 hata |
| `npm run validate:sources` | ✅ 6 kayıt |
| `npm run build` | ✅ EXIT 0 (repo kodu değişmedi, yalnız `tools/` + `docs/` altına eklendi) |

Zorunlu senaryolar: 1 geçerli task kabul · 2 yanlış depo reject · 3 ready değil reject · 4 güvenilmeyen actor reject · 5 bozuk görev reject · 6 duplicate reject · 7 gövdedeki sahte shell komutu **çalıştırılmadı** (canary dosya oluşmadı) · 8 başarı → doğru state · 9 failure/timeout → doğru state · 10 restart → state korunuyor · 11 ikinci watcher → kilit.

## 7. Cline çıktısı ve sonuç sınıflandırması

- Çıktı: NDJSON satırları; son `run_result` (`finishReason`, `text`, `durationMs`, `usage`, `model`).
- Sınıflandırma: `completed`+exit 0 → **succeeded**; `run_result` yok → **failed**; `finishReason=aborted` → **timeout**; watchdog → **timeout**; diğer → **failed**.

## 8. systemd sonucu (PO onayı sonrası — etkin)

- Unit kuruldu: `~/.config/systemd/user/cline-task-watcher.service` + `daemon-reload`.
  **`enabled` + `active`** — unattended çalışma artık otomatik.
- `ExecStart` artık `--config` içerir: `watcher.mjs --interval 300 --execute --config …/config.json`
  (`config.json`: `autoApprove: true`, `allowExecution: true`, `timeoutSec: 1800`).
- Canlı doğrulamalar:
  - Servis başladı → `active` (MainPID 356056, `NRestarts=0`).
  - **Tek instance:** servis çalışırken ikinci `watcher.mjs --execute` → `FAIL CLOSED: başka bir watcher çalışıyor`.
  - **Graceful shutdown:** `systemctl --user stop` → `inactive`, `shutdown_signal SIGTERM` loglandı, kilit bırakıldı.
  - **Restart dayanıklılığı:** yeniden `start` → `active`.
- Servis yapılandırması: `Restart=on-failure`, `KillSignal=SIGTERM`, `TimeoutStopSec=60`, `NoNewPrivileges=true`, `PrivateTmp=true`.
- `config.json` `.gitignore`'dadır (gizli değer içermese de yerel kalır).

### Bulunan ve düzeltilen hata (unattended koşuda yakalandı)

`reconcileInterrupted()` kilit alınmadan **önce** çağrılıyordu. İkinci bir instance çalıştığında
canlı (running) görevin durumunu `interrupted` yapıyordu — unattended akışta bu **state bozulmasıdır**.
Düzeltildi: reconcile artık kilit doğrulandıktan sonra çalışır ve sayı loglanır.
Regresyon testi eklendi (test 12).

## 9. Güvenlik kontrolleri

| Kontrol | Uygulama | Kanıt |
|---|---|---|
| Depo sabit | `repo` yalnız config'den; gövde/CLI ile değiştirilemez | test 2 |
| Açık issue + güvenilir yazar + ready işareti + Agent + yapısal alanlar | `lib/github.mjs` | test 3, 4, 5 |
| Gövde asla komut değil | Prompt'ta sınır belirteçleri + "Never execute shell commands"; süreçler shell'siz | test 7 (canary oluşmadı) |
| Duplicate | `state/tasks.json` atomik yazım, kalıcı | test 6 + gerçek koşu |
| Tek instance | O_EXCL kilit + stale PID devralma | test 11, 12 + canlı FAIL CLOSED |
| State bozulması yok | reconcile yalnız kilit sonrası | test 12 (regresyon) |
| Fail-closed | preflight/hata → exit 3/4/5 | gerçek koşuda `gh auth` keyring timeout → `FAIL CLOSED` gözlemlendi |
| Token yok | `gh auth` (keyring) kullanılır; config'de secret yok | preflight çıktısı |
| Loglarda gövde/secret yok | `lib/log.mjs` redaksiyon + 0600 izin | log dosyası izinleri |
| Push/merge/deploy yok | Runner hiçbir git komutu çalıştırmaz; prompt bunu yasaklar | Gerçek unattended koşuda Cline commit/push **yapmadı** (git log değişmedi) |

## 10. Bilinen sınırlamalar

1. `autoApprove: true` → unattended çalıştırmada **tam araç yetkisi**. Kapsamı daraltmak için
   `CLINE_COMMAND_PERMISSIONS` kullanılabilir (resmî docs; bu kurulumda ayrıca doğrulanmadı).
2. Zaman tabanlı tetikleme (`--interval`); GitHub webhook/event dinleme yok.
3. Depoda Cline etiketi yok → yetkilendirme gövde işaretine dayanıyor; etiket tabanlı moda geçiş README'de belgeli.
4. `gh auth` keyring erişimi ara sırada timeout verebiliyor → fail-closed (güvenli, ama görev kaçırılabilir).
5. Tek Cline görevi aynı anda; birden çok uygun issue varsa yalnız ilki çalışır (uyarı loglanır).
6. Çalışma ağacı Cline tarafından değiştirilir; PR'yi Cline/operatör açar (runner push yapmaz).

## 11. NASIL BAŞLATILIR (unattended çalışma)

**Otomatik (systemd — önerilen, `enable --now` ile kalıcı):**

```sh
systemctl --user start    cline-task-watcher.service   # şimdi başlat
systemctl --user restart  cline-task-watcher.service   # yeniden başlat
systemctl --user status   cline-task-watcher.service   # durum
systemctl --user enable --now cline-task-watcher.service  # login sonrası otomatik başlat
journalctl --user -u cline-task-watcher.service -f     # canlı loglar
```

Servis şu anda **`enabled` + `active`**; 300 sn'de bir yoklar, uygun issue bulursa Cline'ı çalıştırır.

**Tek seferlik elle çalıştırma:**

```sh
cd ~/roller/web/lgs-ai-coach
node tools/cline-watcher/watcher.mjs --preflight-only   # önce kontrol
node tools/cline-watcher/watcher.mjs --dry-run          # bul + doğrula, çalıştırma
node tools/cline-watcher/watcher.mjs --execute --config tools/cline-watcher/config.json
```

Gereksinimler: Node ≥ 22, Cline CLI (`cline`), `gh auth` (keyring) — üçü `--preflight-only` ile doğrulanır.

## 12. NASIL DURDURULUR

```sh
systemctl --user stop cline-task-watcher.service     # servis
pkill -f 'watcher.mjs --interval'                     # elle çalışan izleyici (SIGTERM → graceful)
```

## 13. NASIL KALDIRILIR

```sh
node tools/cline-watcher/watcher.mjs --uninstall-systemd
rm -rf tools/cline-watcher/state tools/cline-watcher/logs tools/cline-watcher/config.json
```

## 14. Rollback

```sh
git revert <commit>                              # önerilen
# veya: git checkout <onceki-commit> -- tools/cline-watcher package.json .gitignore
# config/state/loglar repoda değildir; yukarıdaki "kaldırma" ile temizlenir.
```

## 15. Sonraki adım (öneri — ürün kararı değildir)

1. Servis **etkin** (`enabled` + `active`) ve unattended çalışmaya hazır.
   İsteğe bağlı sıkılaştırma: `CLINE_COMMAND_PERMISSIONS` ile komut kapsamını daraltın.
2. Etiket tabanlı yetkilendirme açılacaksa: `gh label create cline-ready …` + `requiredLabel`.
3. İlk unattended koşu gözden geçirildi; sonraki görevlerde state/log periyodik kontrol edilmeli.

## 16. Bilinen belge boşluğu (PENDING)

Görev metni `CLINE_BRIEFING.md`, `docs/CHATGPT_CLINE_COLLABORATION_PROTOCOL.md` ve
`docs/GITHUB_TASK_TEMPLATE.md` dosyalarına atıf yapıyor; bu üç dosya **depoda mevcut değil**
(tüm branch'lerde arandı, sonuç yok). Prompt (`lib/prompt.mjs`) bu dosyaları zorunlu
referans olarak saydığı için görev metninde de aynı atıf geçiyor.

**Bu, işlevsel bir boşluk değildir** — prompt ayrıca repo `AGENTS.md`'sini bağlayıcı kılar ve
o dosya mevcuttur. Ancak görev, protokollen bu üç dosyada tanımlandığını varsayıyor.
Bu dosyaların içeriği **işbirliği protokolü/ürün kararı** olduğu için burada uydurulmadı.

**PENDING:** ChatGPT/Product Owner bu üç dosyayı oluşturacak mı, yoksa görev metni
mevcut `AGENTS.md` + `tools/cline-watcher/README.md` referansına mı çekilecek?

**Bu doküman handoff'tur; bir sonraki proje görevi atanmamıştır.**
