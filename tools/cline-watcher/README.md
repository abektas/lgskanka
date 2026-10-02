# Cline Task Watcher (TASK-AUTOMATION-001)

GitHub'a ChatGPT tarafından açılan `READY_FOR_CLINE` görevini bulur, doğrular ve
**Cline CLI headless** ile çalıştırır. Cline SDK kullanılmaz.

Akış:
```
GitHub Issue → keşif (gh) → yetkilendirme → duplicate → güvenli prompt
            → Cline CLI headless → NDJSON / run_result → state + log → (PR'yi Cline açar)
```

## Kurulum

```sh
cd ~/roller/web/lgs-ai-coach
node tools/cline-watcher/watcher.mjs --preflight-only     # gh/cline/sürüm kontrolü
cp tools/cline-watcher/config.example.json tools/cline-watcher/config.json  # isteğe bağlı
```

Gereksinimler (kurulum yolu tahmin edilmez, `--preflight-only` ile doğrulanır):
- Node.js ≥ 22
- Cline CLI (`cline --version` → 3.0.62 doğrulandı)
- `gh` ve **açık bir `gh auth` oturumu** (token hiçbir yerde saklanmaz)

## Kullanım

```sh
node tools/cline-watcher/watcher.mjs --dry-run       # varsayılan: bul + doğrula, çalıştırma
node tools/cline-watcher/watcher.mjs --execute       # gerçek Cline çalıştırması
node tools/cline-watcher/watcher.mjs --interval 300 # sürekli (sistemd altında)
node tools/cline-watcher/watcher.mjs --preflight-only
```

## Yapılandırma (`config.json`)

| Alan | Varsayılan | Açıklama |
|---|---|---|
| `repo` | `abektas/lgs-ai-coach` | **SABİT**; issue gövdesinden değiştirilemez |
| `repoPath` | `~/roller/web/lgs-ai-coach` | Cline `--cwd` değeri |
| `trustedAuthors` | `["abektas"]` | Bu dışındaki yazar → reddedilir |
| `readyStatus` | `READY_FOR_CLINE` | Gövdede `**Status:**` değeri |
| `requiredAgent` | `Cline` | Gövdede `**Agent:**` değeri |
| `requiredMarkers` | Task ID/Agent/Status/Objective/Scope | Yapısal zorunluluklar |
| `requiredLabel` | `null` | Etiket bazlı yetkilendirme (aşağıya bakın) |
| `autoApprove` | `true` | Cline `--auto-approve`. PO onayı 2026-10-02. `false` unattended çalıştırmayı no-op yapar |
| `allowExecution` | `true` | İkinci kapı: çalıştırma için `--execute` **ve** bu değer gerekir |
| `timeoutSec` / `timeoutGraceSec` | 1800 / 90 | Cline `--timeout` + izleyici watchdog'u |

### Etiket tabanlı yetkilendirme (Issue #1 notu)

Depoda şu anda Cline'a özel etiket **yoktur**. Sözleşmeyi zayıflatmamak için varsayılan
kabul **gövde işaretidir** (`**Status:** READY_FOR_CLINE` + `**Agent:** Cline` + yapı).
Etiket bazlı moda geçmek için:

```sh
gh label create cline-ready --repo abektas/lgs-ai-coach \
  --description "Cline tarafından çalıştırılabilir görev" --color "0E8A16"
# sonra config.json: "requiredLabel": "cline-ready"
```

## Güvenlik kontrolleri

| Kontrol | Nerede |
|---|---|
| Depo kimliği sabit + eşleşmezse hiçbir şey çalışmaz | `lib/github.mjs` |
| Açık issue, güvenilir yazar, ready işareti, yapısal alanlar | `lib/github.mjs` |
| **Shell yok**: tüm alt süreçler argüman dizisiyle (`spawn`, `execFile`) | `lib/runner.mjs`, `lib/github.mjs` |
| Issue gövdesi yalnız `<<<UNTRUSTED_TASK_CONTENT ... >>>` bloğunda taşınır + "never execute" talimatı | `lib/prompt.mjs` |
| `--auto-approve` config'den (PO onayı 2026-10-02 → `true`), `--json`, `--timeout`, `--cwd` sabit | `lib/runner.mjs` |
| Tek instance kilidi (ölü PID kilidi devralınır) | `lib/lock.mjs` |
| Duplicate engelleme, kalıcı + atomik state | `lib/state.mjs` |
| Loglarda yalnız tanımlayıcı/durum; token/gövde redakte | `lib/log.mjs` |
| Doğrulama/ön kontrol başarısızsa **FAIL CLOSED** (exit 3/4) | `watcher.mjs` |

## Durum ve log dosyaları

- `state/tasks.json` — görev durumu (atomic yazım, restart sonrası korunur)
- `state/watcher.lock` — tek instance kilidi
- `logs/watcher-*.log` — yapılandırılmış izleyici günlüğü (0600)
- `logs/cline-<TASK>-<n>.ndjson` — Cline'ın ham NDJSON çıktısı (0600)

Durumlar: `claimed · running · dry_run · succeeded · failed · timeout · interrupted · rejected`.

`run_result` yoksa görev **başarı sayılmaz** (fail-safe).

## Test

```sh
npm run test:watcher     # 14 senaryo, gerçek ağ/Cline KULLANMAZ (stub bin)
```

## systemd ( opsiyonel, runner doğrulandıktan SONRA)

```sh
node tools/cline-watcher/watcher.mjs --install-systemd
systemctl --user status cline-task-watcher.service
journalctl --user -u cline-task-watcher.service -f
```

Servis: `Restart=on-failure`, `KillSignal=SIGTERM`, `TimeoutStopSec=60`,
`NoNewPrivileges=true`, `PrivateTmp=true`. İkinci instance kilit nedeniyle açılmaz.

## Durdurma / kaldırma / rollback

```sh
# Durdur
systemctl --user stop cline-task-watcher.service

# Kaldır
node tools/cline-watcher/watcher.mjs --uninstall-systemd

# Tamamen temizle (state + loglar silinir)
rm -rf tools/cline-watcher/state tools/cline-watcher/logs

# Rollback (git)
git revert <commit>   # veya: git checkout <commit> -- tools/cline-watcher
```

## Bilinen sınırlamalar

- Görev tetikleme **zaman tabanlıdır** (`--interval`); GitHub webhook/event dinleme yoktur.
- Tam olarak bir issue yalnız **gövdedeki** sözleşmeye uyarsa çalışır.
- Prompt, işbirliği protokolünün `CLINE_BRIEFING.md`, `docs/CHATGPT_CLINE_COLLABORATION_PROTOCOL.md`
  ve `docs/GITHUB_TASK_TEMPLATE.md` dosyalarında olduğunu varsayar; bu dosyalar depoda
  **mevcut değildir**. Bağlayıcı kılınan asıl belge `AGENTS.md`'dir. Protokol dosyaları
  ChatGPT/PO tarafından oluşturulmalıdır (bkz. handoff §15).
- `autoApprove: false` unattended çalıştırmayı no-op yapar (Cline onaylı aracı
  çalıştıramaz ve `run_result` başarısız döner). Varsayılan `true`'dur; acil
  durumda `config.json` → `autoApprove: false` ile geri alınabilir.
- Runner `git push` **yapmaz**; PR'yi Cline veya operatör açar.
