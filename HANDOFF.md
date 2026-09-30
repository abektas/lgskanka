# LGS AI Coach — Devralma ve Doğrulama Raporu

**Tarih:** 2026-09-30
**Kapsam:** Kaynak koduna ve çalışan servise **dokunulmadan** yapılan production doğrulaması
**Kapsam dışı (bilinçli olarak yapılmadı):** systemd yönlendirmesi, eski dizin arşivleme, MemoryGame entegrasyonu

---

## 0. Değişmezlik kanıtı (dokunulmadı)

| Kontrol | Öncesi | Sonrası | Sonuç |
|---|---|---|---|
| `app/ components/ data/ scripts/` md5 ağacı | `689a963b…` | `689a963b…` | ✅ **Birebir aynı** |
| systemd servisi (port 3000) | PID 2324 | PID 2324 | ✅ Yeniden başlatılmadı |
| `.env.local` | — | — | ✅ Okundu, **değiştirilmedi** |
| `next.config.ts`, `package.json` | — | — | ✅ Dokunulmadı |

**Yalnızca şunlar yapıldı:**
- `.next` yeniden üretildi (build artifact'i — kaynak kod değil)
- Önceki build yedeklendi → `.next.bak-handoff-20260930/` (117 MB, BUILD_ID `UkdH0WZp6-FLTYFeUJSR7`)
- Test sunucusu port **3100**'de açıldı, test sonrası **kapatıldı**
- Bu doküman (`HANDOFF.md`) yazıldı

---

## 1. 🚨 AI SAĞLAYICI ENGELLİ — kök neden doğrudan doğrulandı

> `npm run test:ai` **gerçek kimlik doğrulama testi değildir.** Sahte HTTP sunucularla
> çalışan bir **fallback/contract testidir**: yalnızca `resolveChain()` mantığını ve
> istek/yanıt şeklini doğrular. **Canlı sağlayıcı doğrulanmamış ve engellidir.**
> **Kök neden: OpenRouter, yapılandırılmış anahtarı tanımıyor (HTTP 401).**

### 1.1 Yerel biçim analizi (değer yazılmadı)

`.env.local` içindeki değer, hiçbir çıktıya veya loga yazılmadan özellik olarak incelendi:

| Özellik | Sonuç |
|---|---|
| Uzunluk | 73 karakter |
| `sk-or-v1-` öneki | **VAR** |
| Önek sonrası | 64 karakter |
| Tümü hex (`0-9a-f`) | **EVET** |
| Boş / baş-son boşluk / tırnak | HAYIR / YOK / HAYIR |
| CRLF / BOM | HAYIR / HAYIR |

→ **Anahtar biçim olarak geçerli.** Yerel bir bozulma (kesilme, satır sonu, kazara eklenmiş
boşluk, tırnak) yok. Bu, kök nedenin yerel dosya bozulması **olmadığını** dışlar.

### 1.2 Doğrudan sağlayıcı ön kontrolü (anahtar yalnızca `Authorization` başlığında)

`https://openrouter.ai/api/v1` adresine, `providers.ts` ile **aynı** yol/başlık/gövde
yapılandırmasıyla istek atıldı. Değer hiçbir çıktıda gösterilmedi.

| # | İstek | HTTP | Güvenli kategori | Süre | Gövde |
|---|---|---|---|---|---|
| 0 | `GET /models` — **anahtarsız** kontrol | **200** | `BASARILI` | 4,30 s | 464 model |
| 1 | `GET /models` — **anahtarlı** | **200** | `BASARILI` | 2,59 s | 464 model |
| 2 | `POST /chat/completions` — `OPENROUTER_MODEL` | **401** | `KIMLIK_DOGRULAMA_BASARISIZ_401` | 0,06 s | 50 B |
| 3 | `POST /chat/completions` — bilinen çalışan model | **401** | `KIMLIK_DOGRULAMA_BASARISIZ_401` | 0,29 s | 50 B |

Gövde yalnızca **kategori belirteci** olarak kaydedildi (`user not found`, `not found`).
Ham upstream mesajı rapora yazılmadı.

### 1.3 `route.ts` yapılandırmasıyla karşılaştırma

| Öğe | `providers.ts` / `route.ts` | Ön kontrol | Durum |
|---|---|---|---|
| Base URL | `OPENROUTER_BASE_URL` → `https://openrouter.ai/api/v1` | Aynı | ✅ **Eşleşiyor** |
| Model | `OPENROUTER_MODEL` → `openrouter/free` | Aynı gönderildi | ✅ **Eşleşiyor** |
| Kimlik başlığı | `authorization: Bearer ${apiKey}` | Aynı | ✅ **Eşleşiyor** |
| `HTTP-Referer` | `AI_APP_URL` → `http://localhost:3000` | Aynı | ✅ **Eşleşiyor** |
| `X-Title` | `LGS AI Coach` | Aynı | ✅ **Eşleşiyor** |
| `temperature` / `max_tokens` | `0.2` / `1200` | Aynı biçim | ✅ **Eşleşiyor** |

**Uygulama yapılandırmasında hata bulunmadı.** Kod, sağlayıcının beklediği yola, başlığa ve
gövde biçimine birebir uygun istek gönderiyor.

### 1.4 Kök neden

Üç bulgu birlikte kök nedeni belirliyor:

1. **Ağ ve DNS çalışıyor** — anahtarsız `GET /models` → 200 (4,30 sn).
2. **Anahtar yerel olarak bozuk değil** — biçim, uzunluk ve karakter sınıfı geçerli.
3. **401 modelden bağımsız** — hem `openrouter/free` hem bilinen çalışan bir model aynı
   `KIMLIK_DOGRULAMA_BASARISIZ_401` döndü. Yani sorun model seçimi, kota veya ağ değil.

→ **Kök neden: OpenRouter tarafında bu anahtar bir kullanıcıya bağlı değil — anahtar
iptal edilmiş, süresi dolmuş veya hesap düzeyinde askıya alınmış.** Uygulama değil,
sağlayıcı engeli.

> **Düzeltilen ifadeler:** Önceki notlarda "anahtar geçersiz" denmişti; bu artık
> **doğrulanmış** bir bulgudur, varsayımdan değil. "test yalan söylüyor" gibi
> nitelemeler kullanılmamalıdır — `test:ai` **kendi kapsamında doğru bir testtir**
> (contract/fallback), yalnızca **canlı sağlayıcı sağlığını ölçmez**. "AI zinciri sağlam"
> ifadesi de kanıtsızdır: zincir mantığı doğru, ama **tek bağımlılık var ve o da engelli**.

### 1.5 Etkin sağlayıcı zinciri

```
AI_PROVIDER = auto
Etkin sağlayıcı sayısı = 1  →  ['openrouter']   ← TEK BAĞIMLILIK, YEDEK YOK
```

Gemini ve local tanımlı olmadığı için zincire hiç girmiyor. Yani tek kırılgan nokta var ve
o nokta şu an engelli.

## 2. Rotalama doğrulama matrisi

**Build ID:** `MQ-i0QRwjgiKVvVmq3QFT`
**Sunucu:** `next start -p 3100` (127.0.0.1, production)
**Önceki build ID (yedekte):** `UkdH0WZp6-FLTYFeUJSR7`

### Sayfa rotaları (hepsi `○ Static`)

| # | URL | HTTP | Süre | Boyut | Render | İçerik doğrulaması | Konsol/sunucu hatası |
|---|---|---|---|---|---|---|---|
| 1 | `/` | **200** | 33 ms | 54.964 | ✅ | ✅ "Şimdi ne yapmalıyım?", "5 Haftalık Deneme Programı" | ✅ yok |
| 2 | `/calis` | **200** | 5,9 ms | 30.266 | ✅ | ✅ soru metni, seçenekler, seviye rozeti | ✅ yok |
| 3 | `/ai-koc` | **200** | 6,9 ms | 39.869 | ✅ | ✅ "H1–H7 hata türleri", teşhis kartları | ✅ yok |
| 4 | `/dersler` | **200** | 5,5 ms | 62.554 | ✅ | ✅ "Üslü İfadeler", "DNA ve Kalıtım" | ✅ yok |
| 5 | `/sinavlar` | **200** | 8,5 ms | 35.993 | ✅ | ✅ 5 haftalık deneme takvimi | ✅ yok |
| 6 | `/kaynaklar` | **200** | 5,1 ms | 37.909 | ✅ | ✅ "MEB Örnek Sorular", EBA | ✅ yok |
| 7 | `/oduller` | **200** | 4,8 ms | 42.897 | ✅ | ✅ "Oyun ekonomisi", "Hafıza Kartları" | ✅ yok |
| 8 | `/ilerleme` | **200** | 4,7 ms | 48.405 | ✅ | ✅ "Mastery bantları", H1–H7 tablosu | ✅ yok |
| 9 | `/profil` | **200** | 7,0 ms | 43.206 | ✅ | ✅ "Profil & Karakter", "Verin ve gizlilik" | ✅ yok |

### Metadata rotaları

| # | URL | HTTP | Süre | Boyut | Content-Type | Sonuç |
|---|---|---|---|---|---|---|
| 10 | `/robots.txt` | **200** | 16 ms | 129 | `text/plain` | ✅ |
| 11 | `/sitemap.xml` | **200** | 4,8 ms | 1.501 | `application/xml` | ✅ |
| 12 | `/icon.svg` | **200** | 4,4 ms | 533 | `image/svg+xml` | ✅ |

### 404 davranışı

| URL | HTTP | Render | Sonuç |
|---|---|---|---|
| `/yok-boyle-bir-sayfa` | **404** | `_not-found` segment'i | ✅ Özel `not-found.tsx` çalışıyor |

### Redirect davranışı (trailing slash → 308)

| İstek | HTTP | Hedef |
|---|---|---|
| `/calis/` | **308** | `/calis` |
| `/ai-koc/` | **308** | `/ai-koc` |
| `/dersler/` | **308** | `/dersler` |
| `/sinavlar/` | **308** | `/sinavlar` |
| `/kaynaklar/` | **308** | `/kaynaklar` |
| `/oduller/` | **308** | `/oduller` |
| `/ilerleme/` | **308** | `/ilerleme` |
| `/profil/` | **308** | `/profil` |

**Özet: 12/12 rota 200, 0 redirect hatası, 0 render hatası, 0 sunucu hatası.**

---

## 3. `/api/ai` uç matrisi

| # | Senaryo | HTTP | Süre | Gövde | Değerlendirme |
|---|---|---|---|---|---|
| 1 | `GET` (desteklenmeyen) | **405** | 19 ms | boş | ✅ Doğru davranış |
| 2 | `POST` geçersiz JSON | **400** | 8 ms | `{"error":"Geçersiz JSON gövdesi."}` | ✅ Doğru |
| 3 | `POST` boş gövde `{}` | **502** | 5,4 s | `attempts: [openrouter 401]` | ⚠️ Zincir çalışıyor, sağlayıcı reddi |
| 4 | `POST` görsel limiti aşımı (8.1 MB > 8 MB) | **413** | 43 ms | `"Görsel çok büyük (8100022 karakter > 8000000)"` | ✅ Doğru, AI çağrısı yapılmadan kesildi |
| 5 | `POST` gerçek payload (yanlış cevap + H4) | **502** | 156 ms | `attempts: [openrouter 401]` | ⚠️ Sağlayıcı 401 → **engelli** (§1.4) |

**Sunucu günlüğü (tüm testler boyunca):** 5 satır, yalnızca başlangıç banner'ı.
```
▲ Next.js 16.3.6
- Local:         http://localhost:3100
✓ Ready in 138ms
✓ Running next.config.ts took 30ms
```
→ **Hiçbir `error`, `exception`, `unhandled` veya `warn` yok.** 502/400/413/405'ler dışarıya doğru dönüyor, sunucuyu düşürmüyor.

---

## 4. Yanlış pozitif analizi: 2 "FAIL" aslında doğru davranış

Otomatik içerik taraması 2 eşleşmeyi bulamadı; ikisi de **gerçek hata değil**:

| Aranan metin | Sonuç | Gerçek neden |
|---|---|---|
| `Soru 1 / 3` | ❌ bulunamadı | React 19 SSR metin ayırıcıları: `Soru <!-- -->1<!-- --> / <!-- -->3`. Sayfa 1'de de aynı desen var → render doğru. |
| `Cevabımı gönder` | ❌ bulunamadı | `study-flow.tsx:180` — `selected === null` iken **"Bir seçenek işaretle"** gösterilir. İlk SSR'de doğru olan bu. |
| `AI koçtan teşhis al` | ❌ bulunamadı | `study-flow.tsx:194` — `{answered && !isCorrect && …}` bloğunda. Yalnızca **yanlış cevap sonrası** render edilir. |
| `Gizlilik bilgilendirmesi` | ❌ bulunamadı | Aynı koşullu blokta. İstemci tarafı etkileşimi gerektirir. |

> Bu davranış plan §7 ile uyumlu: hata analizi arayüzü öğrenci yanlış cevabı verdikten sonra açılır. Sunucu tarafı render'da görünmememesi **doğru**.

**⚠️ Doğrulanamayan alan:** Yanlış cevap sonrası akış (koş seçimi → "AI koçtan teşhis al" → API çağrısı → sonuç paneli) **hiçbir headless testte çalıştırılamadı**. Bu, `study-flow.tsx`'in en kritik yolu. Tarayıcıda manuel test gerekir.

---

## 5. Ortam değişkeni durumu (değerler gösterilmedi)

`.env.local` okundu, **hiçbir değer bu rapora yazılmadı**.

### Gerekli anahtarlar

| Anahtar | Durum | Açıklama |
|---|---|---|
| `GEMINI_API_KEY` | ❌ **YOK** | Dosyada hiç tanımlı değil (yorum satırında) |
| `OPENROUTER_API_KEY` | ⚠️ **TANIMLI, sağlayıcı 401 ile engelli** | 73 krk, biçim geçerli. Doğrudan ön kontrolde `POST /chat/completions` → **401** (§1.2/1.4) |
| `LOCAL_AI_BASE_URL` | ❌ **YOK** | Yerel LM Studio/Ollama tanımlı değil |

### Opsiyonel ayarlar

| Anahtar | Durum |
|---|---|
| `OPENROUTER_MODEL` | ✅ TANIMLI |
| `AI_PROVIDER` | ✅ TANIMLI (`auto`) |
| `GEMINI_MODEL`, `LOCAL_AI_MODEL`, `LOCAL_AI_API_KEY` | Yok → varsayılan |
| `AI_FALLBACK_ORDER` | Yok → varsayılan sıra |
| `AI_TIMEOUT_MS` | Yok → varsayılan 45.000 |
| `AI_MAX_PROMPT_CHARS` | Yok → varsayılan 4.000 |
| `AI_MAX_IMAGE_BYTES` | Yok → varsayılan 8.000.000 (testte doğrulandı) |
| `AI_APP_URL` | Yok → varsayılan `http://localhost:3000` |

### Etkin sağlayıcı zinciri

```
AI_PROVIDER = auto
Etkin sağlayıcı sayısı = 1  →  ['openrouter']   ← TEK BAĞIMLILIK, YEDEK YOK
```

### Güvenli test yöntemi (reçete)

**1. Yeni anahtar alın** (değeri hiçbir çıktıya yazmayın):
- Tavsiye: `GEMINI_API_KEY` → https://aistudio.google.com/apikey (ücretsiz katman)
- Alternatif: `OPENROUTER_API_KEY` → https://openrouter.ai/keys
- Ücretsiz alternatif: `LOCAL_AI_BASE_URL=http://localhost:1234/v1` (LM Studio)

**2. Kimlik doğrulamayı doğrudan test edin.** ⚠️ `GET /models` **kimlik
doğrulaması yapmaz** — anahtarsız da 200 döner (§1.2 satır 0-1). Bu uçu test etmeyin.
Gerçek test yazma ucudur:
```bash
curl -s -o /dev/null -w '%{http_code}\n' https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"openai/gpt-4o-mini","messages":[{"role":"user","content":"ping"}],"max_tokens":1}'
# Beklenen: 200    |    401 = anahtar yine engelli
# Anahtari ne konsola ne dosyaya yazdirin; yalnizca HTTP kodunu okuyun.
```

**3. Zincir doğrulaması:**
```bash
node -e '
  const p = require("./.next/server/app/api/ai/providers.js");
' 2>/dev/null || echo "ESM modülü; doğrudan import edin"
```
Beklenen: `['gemini','openrouter']` gibi **en az 2** sağlayıcı (yedeklilik için).

**4. Uçtan uca:**
```bash
cd /home/selam/roller/web/lgs-ai-coach
npm run build
PORT=3100 npx next start -p 3100 &
curl -s -X POST http://127.0.0.1:3100/api/ai \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"test","question":{"text":"2+2?"},"studentAnswer":"3","reason":"İşlem hatası","voiceTranscript":""}'
# Beklenen: 200 + {"answer":"...","provider":"...","model":"..."}
```

**5. `test:ai`'e güvenmeyin** — sahte sunucular kullanır, gerçek anahtarı doğrulamaz.

---

## 6. Sistem yönlendirme uyarısı (düzeltilmedi)

İki ayrı proje dizini var. **Çalışan servis eskisini sunuyor.**

| | `~/roller/web/lgs-ai-coach` (bu dizin) | `~/lgs-ai-coach` |
|---|---|---|
| Sayfa | 9 | **1** |
| `globals.css` | 2.438 satır | **2 satır** |
| `app/page.tsx` | 334 satır | 88 satır |
| AI katmanı | 3 sağlayıcı + yedekleme | tek sağlayıcı, yedekleme yok |

**systemd:** `lgs-ai-coach.service` → `WorkingDirectory=/home/selam/lgs-ai-coach`
**Sonuç:** `localhost:3000/calis`, `/ai-koc`, `/profil` → **404** (o build'de o sayfalar yok)
**Kanıt:** Canlı API'nin döndürdüğü `"OPENROUTER_API_KEY tanımlı değil. .env.local dosyasını kontrol edin."` metni yalnızca eski dizindeki `route.ts`'te var; bu dizindeki kodda o metin **yok**.

**Düzeltme (onay bekliyor):**
```bash
# systemd unit'inde WorkingDirectory ve PATH'i güncelle:
#   WorkingDirectory=/home/selam/roller/web/lgs-ai-coach
#   PATH=.../roller/web/lgs-ai-coach/node_modules/.bin:...
systemctl --user daemon-reload
systemctl --user restart lgs-ai-coach.service
```
Eski dizin arşivlenebilir veya bırakılabilir — kararı size bırakıyorum.

---

## 7. Yazılmış ama bağlanmamış kod

| Dosya | Satır | Durum |
|---|---|---|
| `components/memory-game.tsx` | 328 | ⚠️ **Hiçbir dosyada import edilmiyor** |
| `components/use-game-rights.ts` | 155 | ⚠️ **Hiçbir dosyada import edilmiyor** |
| `app/globals.css` `.memory-*` | 0 | ❌ **Stili hiç yok** — bağlansa bile çıplak |

`game-center.tsx` tüm oyunlarda *"Oyun modülü bu sürümde geliştirme aşamasında"* yazıyor. Mini 2048 hiç yazılmamış (yalnızca `content.ts`'te isim olarak var).

**Onay olmadan değiştirilmedi.**

---

## 8. Diğer gözlemler

- **Git repo yok** (`fatal: not a git repository`) — plan §65 "her kritik değişiklik öncesi backup al" diyor, ancak sürüm güvenliği yok. `.next.bak-handoff-20260930/` yalnızca build artifact'i yedeğidir, kaynak kod yedeği değildir.
- **Eski kaynak kopyaları:** `app/page.tsx.backup`, `app/page.tsx.backup-20260927-223554`, `app/page.tsx.save` (her biri 88 satır) kaynak ağacında duruyor.
- **Fotoğraf gizliliği:** UI "kalıcı olarak silindi" diyor, `study-flow.tsx` fotoğrafı React state'inde tutmaya devam ediyor. Backend silme mevcut değil — plan §23/§50 henüz uygulanmamış.
- **Ses sistemi:** `profil/page.tsx` "60 saniye" ve mikrofon izni vaat ediyor; `MediaRecorder` kodu hiç yok (plan §22).
- **Statik sayfalar** `Cache-Control: s-maxage=31536000` alıyor — `/calis` gibi "bugünün çalışması" içeren sayfalarda demo veri 1 yıl önbelleğe alınıyor. Gerçek veri bağlandığında dikkat edilmeli.

---

## 9. Önerilen sıra

1. **OpenRouter engelini gider** — yeni anahtar veya ikinci bir sağlayıcı tanımla (§1.4, §5)
2. **Sistemd yönlendirmesini onayla** → §6
3. **Git repo başlat** (sürüm güvenliği) → §8
4. **MemoryGame'i CSS + GameCenter entegrasyonu ile bağla** → §7
5. Mini 2048 yaz → §7
6. Tarayıcıda manuel test: yanlış cevap → H-kodu → AI teşhis akışı → §4

---

**Bu rapor hazırlanırken kaynak koduna, çalışan servise ve `.env` dosyalarına müdahale edilmemiştir.**
