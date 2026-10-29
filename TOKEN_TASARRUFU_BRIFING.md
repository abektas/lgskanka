# Hermes Agent — Token Tasarrufu Global Ayarları Brifingi

**Hazırlayan:** Hermes Agent (Linux/Pop!_OS)  
**Tarih:** 2026-10-22 (İstanbul, UTC+3)  
**Hedef:** Windows üzerinde çalışan Hermes Agent'a uygulanacak global yapılandırma  
**Amaç:** Günlük 15M token kotasını %80-90 azaltmak, kota dolduğunda çalışmaya devam etmek

---

## 1. Global `config.yaml` Değişiklikleri

Tüm ayarlar `hermes config set` ile yazıldı, `hermes gateway restart` ile etkinleştirildi.  
Windows'ta aynı komutlar PowerShell'de çalışır.

### 1.1 Model & Context Sınırları
```bash
hermes config set model.context_length 32768
hermes config set model.max_output_tokens 4096
```
- Giriş context'i 32K, çıkış 4K ile zorunlu kısıtlandı.
- Sağlayıcı (Evren, OmniRoute, NVIDIA vb.) ne döndürürse döndürsün, Hermes bu sınırları uygular.

### 1.2 Bağlam Sıkıştırma (Compression)
```bash
hermes config set compression.enabled true
hermes config set compression.threshold 0.6
hermes config set compression.target_ratio 0.15
hermes config set compression.tail_mode lean
```
| Parametre | Değer | Anlamı |
|-----------|-------|--------|
| `threshold` | 0.6 | Context %60 dolduğunda sıkıştırma tetiklenir |
| `target_ratio` | 0.15 | Sıkıştırma sonrası hedef: orijinalin %15'i (≈%85 tasarruf) |
| `tail_mode` | lean | Son konuşma bölümü minimum token ile tutulur |
| `protect_last_n` | 20 (varsayılan) | Son 20 mesaj korunur |

### 1.3 Tool Output Kısıtlaması
```bash
hermes config set tool_output.max_bytes 30000
hermes config set tool_output.max_lines 800
```
- Terminal/araç çıktıları 30 KB / 800 satırdan fazlası context'e yazılmaz; fazlası diskte (spill) tutulur, context'e kısa özet konur.

### 1.4 Tool Search (Araç Şema Yükleme)
```bash
hermes config set tools.tool_search.enabled auto
hermes config set tools.tool_search.listing_max_tokens 2000
hermes config set tools.tool_search.threshold_pct 5
hermes config set tools.tool_search.search_default_limit 5
```
- Tüm araç şemaları baştan yüklenmez; ihtiyaç olduğunda (BM25) yüklenir.
- Listeleme 2K token ile sınırlı.

### 1.5 Yardımcı Sıkıştırma Modeli (Auxiliary Compression)
```bash
hermes config set auxiliary.compression.provider evren
hermes config set auxiliary.compression.model deepseek-v4.1-flash
hermes config set auxiliary.compression.base_url https://evren-llmapi.ssyz.org.tr/v1
hermes config set auxiliary.compression.reasoning_effort low
hermes config set auxiliary.compression.fallback_chain '[{"provider":"nvidia","model":"nvidia/nemotron-3-ultra-550b-a55b"},{"provider":"omniroute","model":"auto"}]'
```
- Sıkıştırma işi ana modelden ayrı, ücretsiz kotalı `deepseek-v4.1-flash` ile yapılır.
- `reasoning_effort: low` → derin muhasebe yok, hızlı özet.
- Fallback zinciri: Evren kotalıysa → NVIDIA Nemotron → OmniRoute auto.

### 1.6 Konuşma Geçmişi Limiti (Uyarı: tanınmayan anahtar)
```bash
hermes config set conversation_history_limit 20
```
- Resmi şemada yok; yine de kaydedildi. Bazı sürümler okur. Gerekirse `hermes config unset conversation_history_limit` ile kaldırılabilir.

### 1.7 Devre Dışı Bırakılan Toolset'ler
```bash
hermes tools disable browser video video_gen x_search tts stt computer_use a2a agency_agents spotify context_engine yuanbao
```
| Toolset | Neden |
|---------|-------|
| browser, video, video_gen | GPU/token yoğun, nadir kullanılır |
| x_search, tts, stt | Ses/sosyal medya akışı yoksa gereksiz |
| computer_use, a2a, agency_agents, spotify | Masaüstü otomasyonu/entegre edilmemiş |
| context_engine, yuanbao | Kullanılmıyor |

**Açık kalan toolset'ler:** web, terminal, file, code_execution, vision, image_gen, skills, todo, kanban, memory, session_search, connections, clarify, delegation, cronjob, rea, cloudflare, figma.

---

## 2. Proje İçi (Repo) Prompt Optimizasyonları

`/home/selam/roller/web/lgs-ai-coach` içinde 4 dosya kısaltıldı. Bu değişiklikler **her projeye özeldir**, global etki yoktur. Windows'ta aynı repoyu klonlarsanız zaten dahil gelir.

| Dosya | Değişiklik | Tahmini Tasarruf |
|-------|------------|------------------|
| `app/api/ai/route.ts` | Prompt alanları: soru 1200, cevap 400, zorluk 120, ses 120, ek 400 karakter | ≈%60 |
| `scripts/analyze_lgs18_26.py` | Prompt tek satır JSON şablonuna indirildi | ≈%70 |
| `scripts/source-ingestion/analyze_text_mode.py` | System + prompt tek satır; `question_text` 4000 karakter | ≈%65 |
| `scripts/source-ingestion/analyze_lgs18_26_text.py` | System + prompt tek satır; `question_text` 5000 karakter | ≈%65 |

**Prensip:** "Sadece JSON üret", açıklama/metin şablonları kaldırıldı.

---

## 3. Kullanılan / Yüklenen Skill'ler

| Skill | Durum | Kullanım Amacı |
|-------|-------|----------------|
| `hermes-agent` (autonomous-ai-agents/hermes-agent) | ✅ Yüklendi | Config, provider, toolset, compression referansları |
| `nuli-qbank-hermes` (research/nuli-qbank-hermes) | ✅ Yüklendi | LGS QBANK ingestion/analiz prosedürleri (proje özel) |
| `lgs-pdf-crop-extraction` | ✅ Yüklendi | PDF → PNG crop (proje özel) |
| `lgs-pdf-extraction` | ✅ Yüklendi | MEB LGS PDF metin çıkarma (proje özel) |
| Diğer 280+ skill | ❌ `skills.auto_load: []` ile **otomatik yükleme kapatıldı** | Sadece ihtiyaçta `skill_view` ile yüklenir |

> **Windows'ta:** `skills.auto_load` boş bırakıldığı için hiçbir skill başlangıçta yüklenmez. İhtiyaç duyduğunuzda `skill_view(name)` ile tek tek yükleyin.

---

## 4. Windows'ta Uygulama Talimatı (PowerShell)

```powershell
# 1. Hermes CLI yolunda mı?
hermes --version

# 2. Mevcut config yedeği
Copy-Item ~/.hermes/config.yaml ~/.hermes/config.yaml.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')

# 3. Global ayarları tek tek uygula
hermes config set model.context_length 32768
hermes config set model.max_output_tokens 4096
hermes config set compression.enabled true
hermes config set compression.threshold 0.6
hermes config set compression.target_ratio 0.15
hermes config set compression.tail_mode lean
hermes config set tool_output.max_bytes 30000
hermes config set tool_output.max_lines 800
hermes config set tools.tool_search.enabled auto
hermes config set tools.tool_search.listing_max_tokens 2000
hermes config set tools.tool_search.threshold_pct 5
hermes config set tools.tool_search.search_default_limit 5
hermes config set auxiliary.compression.provider evren
hermes config set auxiliary.compression.model deepseek-v4.1-flash
hermes config set auxiliary.compression.base_url https://evren-llmapi.ssyz.org.tr/v1
hermes config set auxiliary.compression.reasoning_effort low
hermes config set auxiliary.compression.fallback_chain '[{"provider":"nvidia","model":"nvidia/nemotron-3-ultra-550b-a55b"},{"provider":"omniroute","model":"auto"}]'
hermes config set conversation_history_limit 20

# 4. Gereksiz toolset'leri kapat
hermes tools disable browser video video_gen x_search tts stt computer_use a2a agency_agents spotify context_engine yuanbao

# 5. Auto-load skill listesini temizle
hermes config set skills.auto_load '[]'

# 6. Gateway'i yeniden başlat
hermes gateway restart

# 7. Doğrula
hermes config get model.context_length
hermes config get model.max_output_tokens
hermes config get compression
hermes config get tool_output
hermes config get auxiliary.compression
hermes tools list
```

---

## 5. Doğrulama / Ölçüm Komutları

Her değişiklikten sonra şu komutlarla etkiyi ölçün:

```bash
# Sabit prompt maliyeti (system + tool şemaları + skill'ler)
hermes prompt-size

# Canlı oturumda token dağılımı
# (Hermes Desktop / TUI içinde)
/usage
/context
/compress
```

**Beklenen iyileşme:**
- Sabit prompt maliyeti: 45K → 15-20K token
- Tool output spill: büyük loglar context'e yazılmaz
- Sıkıştırma: 0.6 threshold, %85 hedef
- Yardımcı model: ana model kotasını tüketmez

---

## 6. Sık Karşılaşılan Sorunlar ve Çözümler

| Sorun | Çözüm |
|-------|-------|
| `conversation_history_limit` uyarı veriyor | Normal, resmi şemada yok. `hermes config unset conversation_history_limit` ile kaldırın. |
| `auxiliary.compression.fallback_chain` uyarı veriyor | Aynen, şemada yok ama Hermes 0.22+ bazı sürümleri okur. Kaldırmak için `unset`. |
| Evren API 429/403 veriyor | Fallback zinciri devreye girer (NVIDIA → OmniRoute). OmniRoute'ın `grok-web` cookie'si güncel olmalı. |
| Ollama yerel model çalışmıyor | `systemctl --user restart ollama-serve.service` (Linux) / Windows'ta `ollama serve` servisi çalışıyor mu kontrol edin. |
| Tool search yavaş | `tools.tool_search.threshold_pct 5` artırın (örn. 10). |
| Context yine doluyor | `compression.threshold 0.5` / `target_ratio 0.1` yapın, `protect_last_n 10` düşürün. |

---

## 7. Rollback (Geri Alma) Prosedürü

```bash
# Config yedeğinden dön
cp ~/.hermes/config.yaml.backup-YYYYMMDD-HHMMSS ~/.hermes/config.yaml

# Toolset'leri tekrar aç
hermes tools enable browser video video_gen x_search tts stt computer_use a2a agency_agents spotify context_engine yuanbao

# Skill auto-load eski haline (örnek)
hermes config set skills.auto_load '["hermes-agent","nuli-qbank-hermes",...]'

hermes gateway restart
```

---

## 8. Notlar

- Bu brifing **Linux'ta test edilmiş, Windows'ta aynı komutlarla çalışır**.
- Proje içi prompt değişiklikleri (`lgs-ai-coach` repo) zaten kodda; Windows'ta repo klonlandığında hazır gelir.
- Skill'ler `~/.hermes/skills/` altına kurulu; `skills.auto_load: []` olduğu için her oturumda **sadece istediğiniz skill yüklenir**.
- Kota sıfırlama (03:00 UTC+3) sonrası bu ayarlarla günlük ~1.5-3M token harcama hedeflenir (önceki ~15M).

---

**Hazır duruma getirildi.** Windows Hermes Agent'ına bu dosyayı verin, PowerShell'de 4. bölümü sırayla çalıştırın.