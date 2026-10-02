# LGS AI Coach — Proje Devralma Raporu

**Tarih:** 2026-10-01
**Branch:** `codex/profile-3d-avatars` (HEAD `efa2509`)
**Kapsam:** Depo incelemesi, çalışan durumun doğrulanması ve devralmayı engelleyen kusurların düzeltilmesi.

---

## 1. Proje nedir

Next.js 16 (App Router, Turbopack) + React 19 + TypeScript ile yazılmış, 8. sınıf öğrencileri için
LGS çalışma koçu. Harici bağımlılık yok (`package.json` yalnızca `next`, `react`, `react-dom`).

| Katman | Yer | Not |
|---|---|---|
| Sayfalar | `app/*/page.tsx` (9 sayfa) | dashboard, calis, dersler, ilerleme, kaynaklar, oduller, profil, sinavlar, ai-koc |
| Bileşenler | `components/` (20 dosya) | oyunlar, çalışma akışı, ses kaydı, profil |
| AI API | `app/api/ai/route.ts` + `providers.ts` | sunucu tarafı, sağlayıcı zinciri |
| Soru bankası API | `app/api/questions/route.ts` | `data/questions/questions.json` (şu an boş) |
| Oyun API | `app/api/games/runner/route.ts` | demo sorularla sunucu tarafı değerlendirme |
| Kaynak boru hattı | `scripts/source-ingestion/` + `tests/source-ingestion/` | Python, MEB PDF içe aktarma (yayın kapılı) |
| Şema | `db/001_question_bank.sql` | PostgreSQL, **uygulanmadı** |
| Referans paket | `data/source-engine/` | Salt-okunur referans kopya (v1.0) |

Öğrenci ilerlemesi şu an tarayıcı `localStorage`'ında (`components/profile-provider.tsx`); sunucu
veritabanı yok.

---

## 2. Doğrulanan durum

| Kontrol | Komut | Sonuç |
|---|---|---|
| Tip kontrolü | `npx tsc --noEmit` | ✅ 0 hata |
| Üretim build | `npm run build` | ✅ 16 rota, exit 0 |
| AI sağlayıcı testi | `npm run test:ai` | ✅ 19/19 (stub sunucular) |
| Kaynak testleri | `npm run test:source` | ⚠️ Öncesi: 1 modül ImportError → ✅ Sonrası: 24 test OK + 3 node testi |
| Kaynak kayıt doğrulama | `npm run validate:sources` | ✅ 6 resmî kayıt |
| Diff temizliği | `git diff --check` | ✅ temiz |

Not: `npm run test:ai` gerçek kimlik doğrulama testi değildir; yalnızca zincir sırasını ve
istek/yanıt sözleşmesini sahte sunucularla doğrular (bkz. HANDOFF.md §1).

---

## 3. Düzeltilen kusurlar

### 3.1 `.env.example` içinde gerçek API anahtarları (gizli anahtar sızıntısı)

**Bulgu:** Çalışma ağacındaki `.env.example`, gerçek Gemini (`AQ.Ab8…`) ve OpenRouter
(`sk-or-v1-3a7b…`) anahtarlarını içeriyordu. `.gitignore` yalnızca `.env`, `.env.local` ve
`.env.*.local` kalıplarını kapsadığı için dosya `git add -A` ile commit edilebilir durumdaydı.
Dosyanın sonu da bozuktu: yinelenen `AI_PROVIDER`/`AI_FALLBACK_ORDER` blokları ve
`NODE_ENV=developmen` olarak kesilmiş satır. Bu, AGENTS.md "sırlar yalnızca yerel ortamda tutulur"
kuralının ihlaliydi.

**Düzeltme:**
- `.env.example` yeniden yazıldı: yalnızca değişken adları ve güvenli yer tutucular; yinelenen blok
  ve kesik satır kaldırıldı; sağlayıcı sırası kodla eşitlendi (openai → gemini → openrouter).
- Kodda kullanılan ama belgelenmemiş `NEXT_PUBLIC_SITE_URL` eklendi (`layout.tsx`, `robots.ts`,
  `sitemap.ts`).
- `.gitignore` sıkılaştırıldı: `.env.*` yoksayılır, `!.env.example` istisnası korunur; böylece
  `.env.example.backup` gibi türev dosyalar da Git dışında kalır.

**Kalan risk:** Gerçek anahtarlar hâlâ `.env.local` içinde (doğru yer). Ancak inceleme sırasında
gizli anahtar taraması maskeyi eksik uyguladı ve terminal çıktısında OpenAI anahtarının bir bölümü
görünür oldu. Bu oturum günlüğü paylaşılacaksa ilgili anahtarların (OpenAI öncelikli) döndürülmesi
(rotate) önerilir. HANDOFF.md §1'de OpenRouter anahtarının 401 döndürdüğü kayıtlıdır; yeni
yapılandırmada OpenAI birincil sağlayıcı olduğu için bu engel zinciri artık doğrudan durdurmaz.

### 3.2 `npm run test:source` kırıktı (eksik fonksiyon)

**Bulgu:** `tests/source-ingestion/test_pipeline.py`, `download_official_pdfs.select_discoveries`
fonksiyonunu import ediyordu; fonksiyon betikte tanımlı değildi →
`ImportError: cannot import name 'select_discoveries'`; modüldeki 24 testin tamamı çalışmıyordu.
Ayrıca `main()` doğrudan `discoveries[:max_pdfs]` kullanıyordu, yani pilot planının "resmî sayfa
bağlantı metnine göre kitapçık seç" adımı uygulanmamıştı
(`docs/superpowers/plans/2026-09-30-meb-source-ingestion-pilot.md`, Task 3).

**Düzeltme (`scripts/source-ingestion/download_official_pdfs.py`):**
- `normalize_anchor_text()`: Türkçe karakterleri ASCII'ye indirir (ı→i, ş→s, ğ→g, ç→c…), böylece
  resmî sayfa metnindeki "Sayısal Bölüm A Kitapçığı" gibi yazımlar eşleşir.
- `select_discoveries(discoveries, booklet)`: yalnızca bağlantı metnini kanıt olarak kullanır;
  eşleşme yoksa boş liste döner, tahmin yapmaz. Kanıtlanan davranış: `SAYISAL_A → sayısal pdf`,
  `SOZEL_A → sözel pdf`, `SAYISAL → sayısal pdf`, `SAYISAL_B → []`, `None → tümü`,
  `MATEMATIK_A → []`.
- `main()` içine `--booklet` eklendi ve seçim bu fonksiyona bağlandı; JSON raporuna `booklet` ve
  `selected_pdf_count` alanları eklendi. Canlı ağ erişimi eklenmedi.


---

## 4. Karar bekleyen konular

1. **AI sağlayıcı katmanı `local` sağlayıcısını kaybetti (onay bekliyor).**
   Working tree'de `providers.ts` yeniden yazılmış: `gemini | openrouter | local` →
   `openai | gemini | openrouter`. Yeni kod, smoke testi ve `.env.example` bu yönle tutarlı ve
   build/test temiz. Ancak:
   - `README.md` ve `AGENTS.md` hâlâ `local` (LM Studio / Ollama / vLLM) sağlayıcısını belgeliyor.
   - AGENTS.md: "planlanmış bir mimari değişiklik onaylanmadıkça mevcut sağlayıcı soyutlaması
     (Gemini, OpenRouter ve yerel sağlayıcılar dahil) izlenir."
   → Seçenekler: (a) OpenAI eklenmesini benimse, README/AGENTS'i güncelle; (b) `local` sağlayıcıyı
   4. halka olarak geri ekle (openai → gemini → openrouter → local); (c) HEAD sürümüne dön.

2. **Yedek/atık dosyalar (silinmedi, çalışma ağacı korundu):**
   - `app/api/ai/providers.ts'` (1229 satır, `'` karakterli bozuk deneme),
     `.backup`, `.backup-openai`, `.before-openai`, `.save` (337–339 satır) ve
     `scripts/ai-providers.smoke.mjs.backup`.
   - `.env.example.backup` (artık `.gitignore` ile korunuyor).
   - Depoda **tracked** durumda: kökteki iki `ChatGPT Image …png` (toplam 3,7 MB),
     `app/page.tsx.backup`, `app/page.tsx.backup-20260927-223554`, `app/page.tsx.save`.
   → Temizlik yapılmadı; onay bekliyor.

3. **Pilot artefakt yolları:** manifestlerdeki `archive_path` kök `data/questions/archive/…`
   yazıyor, dosyalar `scripts/source-ingestion/data/questions/archive/…` altında. Boru hattı
   `scripts/source-ingestion` dizininden çalıştırıldığı için oluşan tutarsızlık; yeniden
   çalıştırmalarda `--archive-dir` / `--manifest-dir` açıkça verilmeli.

4. **Boş dizin:** `lib/ai/__tests__/` kullanılmıyor.

5. **Eski rapor:** `HANDOFF.md` (2026-09-30) "Git repo yok" diyor; repo artık mevcut. §7'deki
   "bağlanmamış kod" tespitleri de aşıldı: `components/game-center.tsx` artık `MemoryGame`,
   `Mini2048` ve `LgsRunner` bileşenlerini import edip kullanıyor.

---

## 5. Bilinen ürün/teknik boşluklar (değiştirilmedi)

- Soru bankası boş: `GET /api/questions` → `{ items: [], count: 0 }`. `VERIFIED` kayıt olmadığı için
  alıştırma akışı demo sorularla (`data/content.ts`) çalışıyor.
- Veritabanı yok: `db/001_question_bank.sql` yalnızca incelenebilir şema; API JSON dosyası okuyor.
- Öğrenci verisi kalıcı değil (localStorage); XP/görev ilerlemesi cihaza bağlı.
- Canlı üretim doğrulaması (gerçek AI çağrısı, gerçek MEB PDF indirme) bu oturumda yapılmadı;
  hiçbir dış ağ isteği gönderilmedi.

---

## 6. Bu görevde değişen dosyalar

| Dosya | Değişiklik |
|---|---|
| `.env.example` | Gerçek anahtarlar kaldırıldı, yinelenen blok silindi, `NEXT_PUBLIC_SITE_URL` eklendi |
| `.gitignore` | `.env.*` yoksayılır, `!.env.example` istisnası korunur |
| `scripts/source-ingestion/download_official_pdfs.py` | `normalize_anchor_text`, `select_discoveries`, `--booklet` |
| `docs/proje-devralma-2026-10-01.md` | Bu rapor |

Commit/push yapılmadı, bağımlılık değiştirilmedi, UI/API davranışı değiştirilmedi.

