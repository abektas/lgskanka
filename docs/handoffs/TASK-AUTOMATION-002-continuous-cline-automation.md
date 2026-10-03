# TASK-AUTOMATION-002 — Sürekli çalışan GitHub → Cline otomasyonu (Handoff)

**Tarih:** 2026-10-03
**Kaynak görev:** GitHub Issue #3 (`READY_FOR_CLINE`, `TASK-AUTOMATION-002`)
**Yürütücü:** Cline CLI 3.0.62 headless (`stealth/space-bunny-alpha`, `cline-pass`), unattended (`--auto-approve true`)
**Sonuç:** `succeeded` · exit 0 · `finishReason: completed` · **792.874 ms (13 dk 13 sn)** · 3.366 mesaj
**Token:** 6.153.440 input / 41.356 output / 5.910.404 cache-read / maliyet 0
**Ham çıktı:** `tools/cline-watcher/logs/cline-TASK-AUTOMATION-002-3.ndjson`
**Durum kaydı:** `tools/cline-watcher/state/tasks.json` → `TASK-AUTOMATION-002#3`

> Bu belge bir **handoff**'tur. Merge, deploy veya yeni görev tetikleme YAPILMAMIŞTIR.

---

## 1. Ne değişti

| Dosya | Değişiklik |
|---|---|
| `tools/cline-watcher/lib/webhook.mjs` | **YENİ** — HMAC-SHA256 doğrulamalı yerel event alıcısı |
| `tools/cline-watcher/lib/health.mjs` | **YENİ** — atomik `state/health.json` gözlemlenebilirliği |
| `tools/cline-watcher/test/automation.test.mjs` | **YENİ** — 14 senaryo (event, health, config, shutdown, runner) |
| `tools/cline-watcher/watcher.mjs` | Sürekli döngü, `--once`/`--status`/`--event-webhook`, graceful shutdown, tur hata kurtarma |
| `tools/cline-watcher/lib/runner.mjs` | `onSpawn`/`onAbort` kancası → çalışan sürecin güvenli sonlandırılması |
| `tools/cline-watcher/lib/config.mjs` | `eventWebhook` + `fallbackIntervalSec: 240` + `minPollIntervalSec: 60` |
| `tools/cline-watcher/lib/github.mjs` | Yalnız hız-sınırı yorumu (davranış değişikliği yok) |
| `tools/cline-watcher/systemd/cline-task-watcher.service` | `--interval 240`, `Restart=always`, `TimeoutStopSec=90` |
| `package.json` | `test:watcher` betiğine `automation.test.mjs` eklendi |

## 2. Mimari

```
GitHub olayı ──HMAC doğrula──▶ 127.0.0.1:8787 /cline-trigger ──▶ notifier ─┐
                                                                          ├──▶ tur
240 sn (4 dk) ────────────────────────── yoklama (fallback) ──────────────┘     │
                                                                                ▼
                                        keşif → yetkilendirme → duplicate → prompt
                                                                                ▼
                                                             Cline CLI headless → NDJSON
```

**Tasarımın kilit noktası:** event yolu yalnızca *"şimdi tara"* sinyali verir. Yetkilendirme
kapıları (`lib/github.mjs`) her iki yolda da **aynı** şekilde çalışır — event atlanırsa
güvenlik sözleşmesi gevşemez.

## 3. Fallback aralığı gerekçesi

**240 sn (4 dk)** seçildi. Görev hedefi 3–5 dk:
- 5 dk sınırının altında ✅
- 3 dk'nın üstünde → GitHub API yükünü ikiye katlamaz ✅
- ≈ 15 `gh issue list` isteği/saat → GitHub saatlik limitinin çok altında ✅
- `minPollIntervalSec: 60` ile aşırı sık yoklama kendi kendini korur (clamp + log)

Uydurma bir ETag/koşullu istek mekanizması **kullanılmadı** — `gh` CLI'da doğrulanmış
karşılığı yok.

## 4. Güvenlik (TASK-AUTOMATION-001 sınırları korundu)

| Kapı | Durum |
|---|---|
| Depo kimliği sabit `abektas/lgs-ai-coach` | ✅ değişmedi |
| Yalnız açık + güvenilir yazar + `READY_FOR_CLINE` + `Agent: Cline` | ✅ değişmedi |
| Gövde `<<<UNTRUSTED_TASK_CONTENT>>>` içinde, asla komut değil | ✅ değişmedi |
| **Shell yok** — tüm alt süreçler argüman dizisiyle | ✅ yeni kod da `spawn`/`execFile` kullanıyor |
| Tek instance kilidi | ✅ kilit, Cline süreci kapandıktan **sonra** bırakılıyor |
| Duplicate engelleme, kalıcı + atomik state | ✅ korundu |
| HMAC `timingSafeEqual` | ✅ yeni |
| Gövde üst sınırı 64 KiB (DoS) | ✅ yeni |
| Secret env **DEĞİŞKEN ADI** ile; değer hiçbir yere yazılmaz | ✅ |
| Event gövdesi loglanmaz/state'e yazılmaz — yalnız tür + numara | ✅ |
| Loglarda token/gövde/PII yok | ✅ test ile doğrulanıyor |
| Doğrulama başarısızsa **fail-closed** | ✅ secret yoksa sunucu hiç başlamıyor |

## 5. Doğrulama (hepsi fiilen koşturuldu)

| Komut | Sonuç |
|---|---|
| `npm run test:watcher` | **29/29 geçti** (15 eski + 14 yeni) |
| `npm run test:source` | 3/3 geçti |
| `npm run test:taxonomy` | 5/5 geçti |
| `npm run test:ai` | 19/19 geçti (contract testi; canlı sağlayıcı sağlığını ölçmez) |
| `npm run validate:sources` | OK — 6 resmi kayıt |
| `npx tsc --noEmit` | Temiz, çıktı yok |
| `npm run build` | Başarılı (BUILD_ID `bQ1gTFbQhJas10jPxgVoQ`), tüm rotalar static |

## 6. Canlı pilot kanıtı

- **Gerçek görev keşfi:** watcher, gövdesi şablona uydurulmuş Issue #3'ü `01:08:53 UTC`'de
  claim etti; `validateIssue()` → `eligible: true`.
- **Gerçek unattended execution:** `autoApprove: true`, Cline 13 dk çalıştı, exit 0.
- **Servisi sonlandırmadan döngüye dönme:** görev bitti → watcher polling/bekleme
  durumunda kalmaya devam etti (state `succeeded`, servis active).
- **Duplicate prevention:** görev bitiminde `TASK-AUTOMATION-002#3` kalıcı state'e yazıldı;
  sonraki turlar aynı issue'u tekrar çalıştırmaz.

## 7. PENDING — karar gerektiren konular (pilot bunları kendi kararıyla ÇÖZMEDİ)

1. **Event-driven için genel erişilebilir relay/tunnel gerekiyor.** Yerel alıcı yalnız
   `127.0.0.1:8787` dinliyor; GitHub bu adrese doğrudan ulaşamaz. Bir tunnel/relay
   (cloudflared, ngrok vb.) seçimi ve işletimi **altyapı/ürün kararıdır** — pilot
   `eventWebhook.enabled: false` ile güvenli varsayılana döndü, yani **şu an üretimde
   çalışan yol 240 sn fallback polling'dir**. Bu bir eksik değil, bilinçli bir güvenlik
   varsayılanıdır.
2. **Etiket tabanlı yetkilendirme** hâlâ kapalı (`requiredLabel: null`). Etiket moduna
   geçiş ürün kararıdır.
3. **`autoApprove: true` unattended çalışmada tam araç yetkisi verir.** Acil sıkıştırma
   için `config.json → autoApprove: false` (fren) hâlâ geçerlidir.
4. **Prompt'ta atıf yapılan protokol dosyaları** (`CLINE_BRIEFING.md`,
   `docs/CHATGPT_CLINE_COLLABORATION_PROTOCOL.md`, `docs/GITHUB_TASK_TEMPLATE.md`) depoda
   **mevcut değil**. Bağlayıcı kılınan asıl belge `AGENTS.md`'dir. Bu görevde sorun
   çıkmadı; dosyaların varlığı hâlâ PO/ChatGPT kararı.

## 8. Çalıştırma / gözlemleme

```sh
systemctl --user status cline-task-watcher.service
journalctl --user -u cline-task-watcher.service -f

# kilide bakmadan, izleyici çalışırken de sorgulanabilir
node tools/cline-watcher/watcher.mjs --status
```

`--status` çıktısı: `watcherRunning`, `lockPresent`, `health` (triggerMode, polls,
eventsReceived, lastRoundStatus, runningTask) ve görev listesi. **Gizli veri içermez.**

## 9. Rollback

```sh
git revert <commit>
# veya: git checkout <onceki-commit> -- tools/cline-watcher package.json
```

Servisi durdurmak: `systemctl --user stop cline-task-watcher.service`.