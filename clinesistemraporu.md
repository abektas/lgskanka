# Cline Programmatic Launch Investigation

**Tarih:** 2026-10-02 · **Tür:** Teknik keşif (OBSERVE → VERIFY → REPORT)
**Amaç:** ChatGPT tarafından GitHub'a `READY_FOR_CLINE` task/Issue oluşturulduğunda, kullanıcı manuel olarak prompt vermeden Cline'ın programatik başlatılabilmesi.
**Kapsam dışı:** Watcher kodu yazılmadı · Issue #1 kapatılmadı · PR oluşturulmadı · hiçbir kod değiştirilmedi.

---

## 1. Installed Cline Environment

| Alan | Değer | Kanıt |
|---|---|---|
| **Version** | **3.0.62** | `cline --version` |
| **Path** | `/usr/local/bin/cline` → `/usr/local/lib/node_modules/cline/bin/cline` | `which` + `readlink -f` |
| **Node** | v22.20.0 (npm 10.9.3) | `node --version` |
| **Platform** | Linux 7.1.1-76070101 x86_64, Pop!_OS 22.04 LTS | `uname -srm`, `/etc/os-release` |
| **Paket bağımlılıkları** | `@cline/agents`, `@cline/core`, `@cline/llms`, `@cline/sdk` (**0.0.83**, kurulu), `@cline/shared` | `cline/package.json` |
| Config/state dizini | `~/.cline` (`--data-dir` ile izole **sandbox** modu mümkün) | `cline --help` |
| Proje config dizini | `<proje>/.cline/{rules,skills,hooks,plugins,mcp.json,agents.yaml}` | CLI Reference |
| Kullanılan provider/model | `cline-pass` / `stealth/space-bunny-alpha` | Fiili headless çalıştırmanın `run_result` çıktısı |

**Not:** `cline config` ve `providers.json` çalıştırılmadı (API anahtarı içerebilir).

---

## 2. Officially Supported Launch Mechanisms

### A) CLI one-shot / headless mode
- **Officially supported: YES**
- **Evidence:** Resmî "CLI Overview → Headless mode" + paket README'si "Headless mode for CI/CD"; yerelde `--json` ile **fiilen çalıştırıldı**.
- **Command/API:** `cline [flags] "<prompt>"` — headless; `--json` NDJSON üretir; stdin pipe veya stdout redirect de headless'i tetikler.
- **Input method:** prompt **tek tırnaklı argüman**; ek bağlam stdin'den (`git diff | cline "review"`); görsel `@./path.png`.
- **Authentication:** `cline auth <provider>`; OAuth sağlayıcıda kimlik yoksa **fail-fast** (gizli tarayıcı akışı açmaz). `-k/--key` env'yi ezer.
- **Result/exit handling:** **Doğrulandı** — başarıda **exit 0**, son satır `{"type":"run_result", finishReason, durationMs, text, model, usage{...totalCost}}`. Argüman hatasında **exit 1** + stderr mesajı.
- **Limitations:** ⚠️ Prompt tırnaklanmazsa CLI onu komut sanıp **exit 1** verir (fiilen doğrulandı: `Unknown command or unquoted prompt: hi`). `--auto-approve` **varsayılan `true`** → otomasyonda `false` verilmeli. Orta hata sırasındaki ayrı exit code ölçülmedi (NOT VERIFIED).

### B) `--json` NDJSON akışı
- **Officially supported: YES** — CLI Reference "JSON Output Format"; yerelde gözlemlenen tipler: `hook_event`, `agent_event` (`done` → `reason`, `text`, `iterations`, `usage`), `run_result` (`finishReason`, `durationMs`, `text`, `model`, `aggregateUsage`).
- **Command:** `cline --json --cwd <path> --timeout <sn> "<prompt>"`
- **Result/exit:** NDJSON satır satır ayrıştırılır (`jq`/Python); nihai `run_result` satırı sonucu özetler.
- **Limitations:** Dokümandaki şema (`type/text/ts/say`) fiili çıktıdan daha sade → **kendi ayrıştırıcı yazılmalı ve gerçek çıktıyla doğrulanmalı**.

### C) Scheduling (cron, hub tabanlı)
- **Officially supported: YES** — Resmî "Scheduling" sayfası **+ bu kurulumda `cline schedule create --help` ile fiilen doğrulandı** (`--cron`, `--prompt`, `--workspace`, `--created-by`).
- **Command:** `cline schedule create "<ad>" --cron "*/10 * * * *" --prompt "<metin>" --workspace /path/to/repo`; yönetim: `list / trigger / pause / resume / delete / executions`.
- **Input/Auth:** prompt + workspace bayraklarıyla; hub daemon aynı provider oturumunu kullanır (otomatik başlar).
- **Result:** **Doğrudan exit code yok** — görev arka planda yürür; sonuç `schedule executions <id>` (durum, süre, token, maliyet) ve hub loglarından okunur.
- **Limitations:** **Zaman tabanlıdır**; "GitHub'da yeni READY_FOR_CLINE oluştu" gibi **olay tabanlı tetik yok**. Kalıcı daemon gerektirir.


### D) `@cline/sdk` (programatik)
- **Officially supported: YES** — Resmî SDK sayfası: *"Use the Cline SDK to run agents from CI/CD pipelines, create automations…"*; bu kurulumda `@cline/sdk@0.0.83` **dolaylı olarak kurulu** (cline'in bağımlılığı) ve `@cline/core`'u re-export ediyor.
- **Command/API:** `npm install @cline/sdk` → `import { Agent } from "@cline/sdk"`; `new Agent({providerId, modelId, apiKey, maxIterations})`, `agent.subscribe(event => …)`, `await agent.run(prompt)`. Node ≥22.
- **Result/exit:** `agent.run()` çözümlenen sonuç döner; event aboneliği ile stream; hata → try/catch.
- **Limitations:** Bu kurulumda **ayrı kurulmamış** → doğrudan import için ayrı kurulum gerekir. Daha düşük seviye: persistans, izinler ve hata yönetimi bize kalır.

### E) Chat connectors (dış kanal)
- **Officially supported: YES** — Resmî README: *"Chat connectors for Telegram, Google Chat, and WhatsApp"*; CLI'da `cline connect <channel> -k <token>`.
- **Kullanım:** Sonuçları mesajlaşma platformuna yönlendirme.
- **Limitations:** 🔴 **GitHub kanalı YOK** (yalnız Telegram / Google Chat / WhatsApp). Kanal **çıktı** tarafıdır, tetikleyici değildir.

### F) ACP (`cline --acp`)
- **Officially supported: YES** — CLI Reference + Usage → ACP.
- **Kullanım:** Zed / JetBrains / Neovim gibi editör istemcileriyle ajan protokolü.
- **Limitations:** Görev kuyruğu/otomasyon mekanizması değildir; senaryoya uymaz.

### G) `--zen` (arka plan hub)
- **Officially supported: YES** (yerel `--help`) — "Start a session that runs in the background hub". Fiilen çalıştırılmadı.
- **Limitations:** Süreç görev bitmeden çıkar → **exit code/sonuç alınamaz**. Senkron doğrulama isteyen runner için uygun değil.

### H) GitHub Actions / CI
- **Officially supported: DOĞRULANAMADI.** Resmî doküman dizininde (`llms.txt`) Cline'a ait bir **GitHub Action** bulunmadı. CI için önerilen yol **CLI veya SDK'yı CI içinde çalıştırmak**. (NOT VERIFIED: üçüncü taraf action'lar.)

### I) MCP
- **Officially supported: YES** (`cline mcp install/uninstall`) — ancak MCP **ajanın araçları** içindir. "GitHub'dan yeni task var mı?" diye soran bir MCP sunucusu tanımlamak **bizim yazacağımız** koddur, Cline'ın yerleşik özelliği değildir.

### J) `--worktree` (yalnız yerel help)
- **Officially supported: resmî referans tablosunda YOK**; bu kurulumun `--help`'inde: *"Auto-create a detached git worktree under ~/.cline/worktrees/ and run the task there."* GitHub task izolasyonu için ilginç — **NOT VERIFIED** (çalıştırılmadı).

---

## 3. Local Linux Automation

Kanıtlanmış akış (yerel Linux, script/systemd tarafından):

```
GitHub'da READY_FOR_CLINE etiketli Issue
  → [BİZİM YAZACAK] watcher (gh CLI/API): issue listesini süzer, etiket/konu doğrular
  → [BİZİM YAZACAK] görev doğrulama + dedup (issue no/state) + prompt şablonu üretimi
  → [BİZİM YAZACAK] state dosyası (issue no → durum / sessionId / log)
  → Cline (resmî, senkron):
        cline --json \
              --cwd /home/selam/roller/web/lgs-ai-coach \
              --auto-approve false \
              --timeout 1800 \
              -p "…" \
              "<tek tırnaklı prompt>"
      (veya ayrı çalışma ağacı; istenirse --worktree)
  → stdout: NDJSON → son satır `run_result`
        finishReason / durationMs / text / usage.totalCost
      stderr: hata mesajları
      process exit code: 0 başarı, 1 hata   (doğrulandı)
  → [BİZİM YAZACAK] sonucu state'e yaz, logla, GitHub'a yorum/etiket olarak geri yaz
  → PR (yalnız onaylıysa) → ChatGPT review → PO onayı → merge

---

## 5. What Is Still Missing

Cline sağlamıyor; bizim yazmamız gerekenler:

| Eksik | Neden |
|---|---|
| **Watcher** — GitHub READY_FOR_CLINE issue/discussion tarama | Cline'da GitHub kanalı **yok**; `schedule` yalnız cron |
| **Task doğrulama** — etiket/şablon/schema kontrolü, "gerçekten task mı" | Cline yalnız metin çalıştırır |
| **Duplicate prevention** — aynı issue için ikinci çalıştırmayı engelleme | `run_result`/`history` var ama "issue → run" eşlemesi yok |
| **State management** — issue no → durum, sessionId, son `run_result` | `cline history --json` oturum verir ama bizim state DB'miz yok |
| **Prompt üretimi** — Issue gövdesi → güvenli, tırnaklanmış tek satır prompt | CLI prompt'un **tırnaklanmasını zorunlu kılıyor** (exit 1 riski) |
| **Çalışma ağacı izolasyonu** — her task için ayrı branch/worktree | `--worktree` var ama doğrulanmadı; PR akışı bizim |
| **Log & maliyet takibi** — stdout NDJSON → kalıcı log | `run_result.usage.totalCost` var, saklama bizim |
| **Hata sınıflandırma & retry** — hangi çıkışta tekrar denenecek | `--retries` ajan içi; süreç seviyesinde retry bizim |
| **Güvenlik sınırları** — `CLINE_COMMAND_PERMISSIONS` politikası, `--auto-approve false`, onay kısıtı | Bayraklar var, **politika yazılmalı** |
| **GitHub'a geri yazma** — yorum/etiket/PR | `gh` CLI elimizde var (`push: true`), kod bizim |

---

## 6. Exact Commands

Çalıştırıp **doğruladığım** komutlar:

```sh
# Ortam
which cline; readlink -f "$(which cline)"; cline --version   # 3.0.62, /usr/local/bin/cline
node --version; uname -srm                                    # v22.20.0, Linux x86_64

# Yüzey
cline --help
cline connect --help ; cline schedule --help ; cline hub --help
cline hook --help ; cline auth --help ; cline history --help
cline mcp --help ; cline plugin --help ; cline doctor --help ; cline config --help
cline schedule create --help        # --cron/--prompt/--workspace/--created-by mevcut

# Headless — BAŞARILI (exit 0)
mkdir -p /tmp/cline-probe
timeout 180 cline --json --cwd /tmp/cline-probe --timeout 120 "Reply with exactly: OK" \
  > /tmp/cline-probe/out.ndjson 2>/tmp/cline-probe/err.txt; echo "EXIT_CODE=$?"
tail -1 /tmp/cline-probe/out.ndjson
# {"type":"run_result","finishReason":"completed","iterations":1,"durationMs":3739,
#  "text":"OK","model":{...},"usage":{...,"totalCost":0}}

# Headless + stdin — BAŞARILI (exit 0)
printf 'PROJE: test\n' | timeout 120 cline --json --cwd /tmp/cline-probe --timeout 90 \
  "Echo back the first word of the piped input"
# EXIT_CODE=0 + run_result

# Hata yolu — BAŞARISIZ (exit 1), tırnaksız prompt reddi
timeout 90 cline --json --cwd /tmp/cline-probe --timeout 45 -P yok-boyle-bir-provider "hi"
# EXIT_CODE=1 ; stderr: "error: Unknown command or unquoted prompt: hi"
#   "Prompt text must be passed as a single quoted argument..."

# Oturum geçmişi (state için)
cline history --json --limit 2
# [{"sessionId":"...","source":"cli","exitCode":0,"status":"completed","interactive":false,
#   "provider":"cline-pass","cwd":"/tmp/cline-probe","prompt":"..."}]

# Kurulu paketler
python3 -c "import json;print(json.load(open('/usr/local/lib/node_modules/cline/node_modules/@cline/sdk/package.json'))['version'])"   # 0.0.83
grep -oE 'CLINE_[A-Z0-9_]+' /usr/local/lib/node_modules/cline/node_modules/@cline/*/dist/*.js | sort -u
# CLINE_DATA_DIR, CLINE_HUB_ADDRESS, CLINE_SESSION_BACKEND_MODE, CLINE_SANDBOX(_DATA_DIR),
# CLINE_HOOKS_DIR, CLINE_RUN_AS_HUB_DAEMON, CLINE_CONNECTOR_*, CLINE_HUB_PORT ...
```

**Çalıştırılmayanlar:** `cline config`, `providers.json` okunmadı (anahtar içerebilir).

---

## 7. Sources

**Yerel (kanıt):**
- `/usr/local/lib/node_modules/cline/README.md` (headless bölümü, connector listesi)
- `cline --help` + alt komut `--help` çıktıları (kurulu 3.0.62)
- `cline/package.json`, `node_modules/@cline/sdk/package.json`
- Fiili headless çalıştırmalar (exit code + NDJSON çıktısı), `cline history --json`

**Resmî Cline dokümanı (docs.cline.bot):**
- `https://docs.cline.bot/llms.txt` — dizin
- `https://docs.cline.bot/cli/overview` — Headless mode, JSON Output Schema, Automation Patterns, `CLINE_COMMAND_PERMISSIONS`
- `https://docs.cline.bot/cli/cli-reference.md` — tüm bayraklar, alt komutlar, env değişkenleri, JSON şeması, config düzeni
- `https://docs.cline.bot/cli/scheduling.md` — `cline schedule create/list/trigger/executions`, hub gereksinimi
- `https://docs.cline.bot/sdk/overview.md` — `@cline/sdk`, `Agent`, `agent.run()`
- `https://docs.cline.bot/cline-overview` — uygulama listesi, SDK'nın CI/CD için önerildiği

**Doğrulanamayanlar:** resmî GitHub Action (yok); `--worktree`, `--yolo`, `CLINE_COMMAND_PERMISSIONS` bu kurulumda fiilen çalıştırılmadı (`--yolo` `--help`'te kabul ediliyor ama referans tablosunda yok; belgelenmiş karşılığı `--auto-approve true`).

---

**STOP:** Watcher kodu yazılmadı, Issue #1 kapatılmadı, PR oluşturulmadı, hiçbir kod değiştirilmedi.

```

**Alternatif (zaman tabanlı, hub destekli):**
```
systemd timer (her N dk) → cline schedule create/list → trigger → executions oku
```
→ GitHub olayına değil **saate** bağlıdır; olay tabanlı READY_FOR_CLINE için doğrudan uygun değil.

---

## 4. Recommended Mechanism for LGS AI Coach

*(Ürün kararı değildir; yalnızca teknik uygunluk.)*

**Teknik olarak en uygun ve kanıtlanmış yol: CLI headless + `--json` + senkron exit code (Mekanizma A+B).**

Gerekçe:
1. **Fiilen doğrulandı** — bu makinede çalıştı, `exit 0` ve `run_result` üretti (prompt, JSON şeması, süre, token/maliyet).
2. **Sonucu programatik alabiliyoruz** — `run_result` + exit code; `--zen` ve `schedule` bu imkânı vermiyor.
3. **Yetkilendirme bize aittir** — `--auto-approve false` + `CLINE_COMMAND_PERMISSIONS` (allow/deny glob) ile komut kapsamı daraltılabilir.
4. **GitHub tarafı Cline'da yok** — connector kanalı GitHub değil, `schedule` olay değil zaman tabanlı. Dolayısıyla GitHub dinleyicisi zaten bizim yazacağımız kod.
5. **SDK** daha güçlü ama daha düşük seviye (kurulum + persistans + izin yönetimi bizde) — CLI ile başlayıp ihtiyaç olursa SDK'ya geçmek teknik olarak mümkün.
