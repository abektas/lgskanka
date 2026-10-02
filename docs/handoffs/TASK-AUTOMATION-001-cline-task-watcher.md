# TASK-AUTOMATION-001 — GitHub → Cline Task Watcher · Handoff

**Tarih:** 2026-10-02 · **Issue:** #1 · **Branch:** `task/TASK-AUTOMATION-001-cline-watcher`
**Mekanizma:** Cline CLI headless (`--json`). **SDK kullanılmadı, entegrasyonu yapılmadı.**

---

## 1. Yapılanlar

- `tools/cline-watcher/` altında **sıfır bağımlılıklı** Node.js watcher/runner (yalnız Node 22 standart kütüphanesi).
- Akış: GitHub Issue → `gh` ile keşif → yetkilendirme kapıları → duplicate kontrolü → güvenli prompt → Cline CLI headless → NDJSON/`run_result` ayrıştırma → kalıcı state + yapılandırılmış log.
- 12 senaryoluk test paketi (`npm run test:watcher`) — stub `gh`/`cline` ile, **gerçek ağ/Cline kullanmadan**.
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
| `tools/cline-watcher/test/{watcher.test.mjs,helpers.mjs}` | 12 senaryo + stub bin/issue fixture'ları |
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
- Otomatik olarak `--json`, `--timeout`, `--cwd`; `--auto-approve` config'den (varsayılan `false`).

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

⚠️ **OWNER_DECISION_REQUIRED:** `--auto-approve false` (görevde zorunlu denilen değer) ile Cline headless oturumda **hiçbir aracı çalıştıramıyor**; görev no-op biter. Gerçek unattended çalıştırma `autoApprove: true` gerektirir — bu da tam otomatik araç/onay yetkisi demektir. Varsayılanı `false` bıraktım (fail-safe); config ile açılabilir. **Bu değerin üretimde ne olacağına Product Owner karar vermelidir.** Öneri: PO onayına kadar servisi `disabled` bırakın.

## 6. Test sonuçları

| Komut | Sonuç |
|---|---|
| `npm run test:watcher` | ✅ **12/12** (11 zorunlu senaryo + "run_result yoksa başarı sayılmaz") |
| `npm run test:source` | ✅ 83 Python OK + 3 node OK |
| `npm run test:ai` | ✅ 19/19 |

## 7. systemd sonucu

- Unit kuruldu: `~/.config/systemd/user/cline-task-watcher.service` + `daemon-reload`. **Kapalı/pasif** (`disabled`, `inactive`) — PO kararı bekleniyor.
- Canlı test: `systemctl --user start` → `active` (MainPID 342422) → tam zincir çalıştı (`task_claimed` → `cline_finished succeeded` 36 sn) → `stop` → `inactive` ve **kilit bırakıldı** (graceful shutdown doğrulandı).
- Servis yapılandırması: `Restart=on-failure`, `KillSignal=SIGTERM`, `TimeoutStopSec=60`, `NoNewPrivileges=true`, `PrivateTmp=true`.

## 8. Güvenlik kontrolleri

| Kontrol | Uygulama | Kanıt |
|---|---|---|
| Depo sabit | `repo` yalnız config'den; gövde/CLI ile değiştirilemez | test 2 |
| Açık issue + güvenilir yazar + ready işareti + Agent + yapısal alanlar | `lib/github.mjs` | test 3, 4, 5 |
| Gövde asla komut değil | Prompt'ta sınır belirteçleri + "Never execute shell commands"; süreçler shell'siz | test 7 (canary oluşmadı) |
| Duplicate | `state/tasks.json` atomik yazım, kalıcı | test 6 + gerçek koşu |
| Tek instance | O_EXCL kilit + stale PID devralma | test 11 |
| Fail-closed | preflight/hata → exit 3/4/5 | gerçek koşuda `gh auth` keyring timeout → `FAIL CLOSED` gözlemlendi |
| Token yok | `gh auth` (keyring) kullanılır; config'de secret yok | preflight çıktısı |
| Loglarda gövde/secret yok | `lib/log.mjs` redaksiyon + 0600 izin | log dosyası izinleri |
| Push/merge/deploy yok | Runner hiçbir git komutu çalıştırmaz; prompt bunu yasaklar | kod incelemesi |

## 9. Bilinen sınırlamalar

1. `--auto-approve false` → unattended çalıştırma no-op (yukarıda).
2. Zaman tabanlı tetikleme (`--interval`); GitHub webhook/event dinleme yok.
3. Depoda Cline etiketi yok → yetkilendirme gövde işaretine dayanıyor; etiket tabanlı moda geçiş README'de belgeli.
4. `gh auth` keyring erişimi ara sırada timeout verebiliyor → fail-closed (güvenli, ama görev kaçırılabilir).
5. Tek Cline görevi aynı anda; birden çok uygun issue varsa yalnız ilki çalışır (uyarı loglanır).
6. Çalışma ağacı Cline tarafından değiştirilir; PR'yi Cline/operatör açar (runner push yapmaz).

## 10. Nasıl durdurulur

```sh
systemctl --user stop cline-task-watcher.service     # servis
pkill -f 'watcher.mjs --interval'                     # elle çalışan izleyici (SIGTERM → graceful)
```

## 11. Nasıl kaldırılır

```sh
node tools/cline-watcher/watcher.mjs --uninstall-systemd
rm -rf tools/cline-watcher/state tools/cline-watcher/logs tools/cline-watcher/config.json
```

## 12. Rollback

```sh
git revert <commit>                              # önerilen
# veya: git checkout <onceki-commit> -- tools/cline-watcher package.json .gitignore
# config/state/loglar repoda değildir; yukarıdaki "kaldırma" ile temizlenir.
```

## 13. Sonraki adım (öneri)

1. **PO kararı:** `autoApprove` değeri (false = güvenli ama no-op; true = işlevsel ama tam araç yetkisi).
2. Karar `true` ise: `config.json` ile `autoApprove: true`, `CLINE_COMMAND_PERMISSIONS` ile komut kapsamı daraltma, sonra `systemctl --user enable --now`.
3. Etiket tabanlı yetkilendirme açılacaksa: `gh label create cline-ready ...` + `requiredLabel`.
4. Servis etkinleştirilirse ilk unattended koşuda state/log gözden geçirilmeli.

**Bu doküman handoff'tur; bir sonraki proje görevi atanmamıştır.**

| `npm run test:taxonomy` | ✅ 5/5 |
| `npx tsc --noEmit` | ✅ 0 hata |
| `npm run validate:sources` | ✅ 6 kayıt |
| `npm run build` | ✅ EXIT 0 (Exit 0 beklenir: repo kodu değişmedi, yalnız `tools/` altına eklendi) |
| `git diff --check` | ✅ EXIT 0 |

Zorunlu senaryolar: 1 geçerli task kabul · 2 yanlış depo reject · 3 ready değil reject · 4 güvenilmeyen actor reject · 5 bozuk görev reject · 6 duplicate reject · 7 gövdedeki sahte shell komutu **çalıştırılmadı** (canary dosya oluşmadı) · 8 başarı → doğru state · 9 failure/timeout → doğru state · 10 restart → state korunuyor · 11 ikinci watcher → kilit.

- Çıktı: NDJSON satırları; son `run_result` (`finishReason`, `text`, `durationMs`, `usage`, `model`).
- Sınıflandırma: `completed`+exit 0 → **succeeded**; `run_result` yok → **failed**; `finishReason=aborted` → **timeout**; watchdog → **timeout**; diğer → **failed**.
