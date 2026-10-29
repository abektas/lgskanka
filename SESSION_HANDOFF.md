# Session Handoff — 2026-10-28 (güncel)

## Active Tasks
- Yok — 4 haftalık çalışma döngüsü + hafta sonu esnekliği TAMAMLANDI ve tarayıcıda doğrulandı.
- Bilinen açık iş: aylık deneme sorularında `topic`/`unit` = null → aylık denemeden pekiştirme üretilemiyor (aşağıda Blockers).

## Yapılanlar (bu oturum)

### 1. Çalışma döngüsü motoru (yeni)
- `lib/cycle.ts` — kayıt tarihinden başlayan 4 haftalık ritim.
  - Hafta içi (Pzt–Cum) → Günlük Alıştırmalar
  - Hafta sonu (Cmt **veya** Paz) → sınav günü: 1-3. hafta Haftalık Test, 4. hafta Aylık Deneme
  - `getEnrollmentDate()` / `setEnrollmentDate()` → localStorage `lgs_enrollment_date`
  - `computeCycleState()` → `{dayType, cycleWeek, cycleNumber, isWeekend, weekendTest, ...}`
  - `ENROLLMENT_CHANGED_EVENT` olayı: kayıt tarihi değişince açık UI'lar yeniden hesaplar
- `scripts/test-cycle.ts` — tarih-bazlı test (30+ assertion). Çalıştır: `npx tsx scripts/test-cycle.ts`

### 2. Kayıt → döngü bağlantısı
- `components/profile-provider.tsx` — `Profile.registeredAt` eklendi.
  - Profil kaydedildiğinde (= sisteme kayıt) `registeredAt` damgalanır ve döngü başlangıcı ona sabitlenir.
  - Eski profiller (registeredAt yok) otomatik migrate edilir; mevcut döngü tarihi korunur.
- `components/cycle-card.tsx` (yeni) — ana sayfadaki 4 adımlı döngü kartı + "Bugün" butonu.
- `components/cycle-badge.tsx` (yeni) — haftalık test / aylık deneme sayfalarında döngü rozeti.

### 3. Sayfa temizliği (planda yeri olmayanlar silindi)
Silinen: `app/dersler`, `app/denetim`, `app/ilerleme`, `app/pilot-2022`, `app/pilot-2022-visual`,
`app/pilot-2025-matematik`, `app/youtube`, `app/api/ai`, `app/api/questions`, `app/api/exams`,
`app/api/pilot-2025-matematik`, `app/api/youtube/*`, `components/pilot-2025-math-flow.tsx`,
`lib/five-week-mock.ts`, `public/pilot-2022-visual`, `public/pilot-2025-matematik`, `app/q-24.png`.

Silme öncesi doğrulama: her bir API/sayfanın UI'dan **çağrılmadığı** grep ile teyit edildi.
Kırık referanslar düzeltildi: `components/search-box.tsx`, `app/page.tsx`, `app/kaynaklar/page.tsx`,
`data/content.ts`, `app/sitemap.ts`, `app/robots.ts`.

### 4. Diğer
- Ana sayfadaki "5 Haftalık Deneme Programı" kartı → `CycleCard` ile değiştirildi (5 haftalık deneme planı yok).
- `app/calis/page.tsx` — döngü bilgisi başlığa eklendi; hafta sonu otomatik yönlendirme (Cmt/Paz → ilgili sınav).
- `app/globals.css` — `.cycle-steps`, `.cycle-step`, `.cycle-today`, `.cycle-badge` stilleri.

## Doğrulama (gerçek çıktı)
- `npm run lint` → exit 0 (tsc temiz)
- `npm run build` → BUILD_DONE, 15 route: `/`, `/calis`, `/pekistirme`, `/aylik-denemeler`,
  `/haftalik-test`, `/sonuclar`, `/profil`, `/kaynaklar`, `/oduller`, 4 API, robots, sitemap
- Silinen rotalar → 404
- `npx tsx scripts/test-cycle.ts` → TÜM TESTLER GEÇTİ
- Tarayıcı (headless Chrome CDP, tarih dondurularak):
  - Cmt 31.10 (1. hf) → `/haftalik-test/` ✓
  - Paz 01.11 (1. hf) → `/haftalik-test/` ✓  ← hafta sonu esnekliği
  - Cmt 21.11 (4. hf) → `/aylik-denemeler/` ✓
  - Paz 22.11 (4. hf) → `/aylik-denemeler/` ✓
  - Çar 28.10 → `/calis/` (dönüş yok) ✓
  - Profil kaydı → `registeredAt` == `lgs_enrollment_date` ✓

## Devreden kararlar (kalıcı)
- **Çalışma döngüsü**: 4 hafta. 1-3. hafta Haftalık Test, 4. hafta Aylık Deneme.
- **Hafta sonu esnek**: cumartesi ve pazar aynı teste girilebilir; öğrenci hangisini isterse o gün çözer.
- **Döngü kayıt anında başlar**: `Profile.registeredAt` (profil kaydı = sisteme kayıt).
- **5 haftalık deneme planı yok** — yalnız haftalık test + aylık deneme.
- **Sonuç ekranı deseni** (haftalık test ve aylık denemede aynı): birincil buton → `/pekistirme`,
  ikincil → `/sonuclar`, `syncReinforcementTasks()` sınav bitince otomatik çağrılır.
- **AI tamamen iptal** — H1-H7 kural tabanlı. `app/api/ai` silindi.
- Karışıklık yaratmayan sayfa kalmadı; menü 9 kalem, hepsi aktif kullanımda.

## Dosyalar
- `lib/cycle.ts` — döngü motoru (yeni)
- `scripts/test-cycle.ts` — döngü testi (yeni)
- `components/cycle-card.tsx` — ana sayfa döngü kartı (yeni)
- `components/cycle-badge.tsx` — sınav sayfası döngü rozeti (yeni)
- `components/profile-provider.tsx` — `registeredAt` + kayıt→döngü bağlantısı
- `app/calis/page.tsx` — döngü başlığı + hafta sonu yönlendirmesi
- `app/page.tsx` — `CycleCard` entegrasyonu
- `app/globals.css` — döngü stilleri

## Blockers
- **Aylık deneme sorularında `topic`/`unit` = null** (1080 soru). Bu yüzden aylık deneme
  sonrası `syncReinforcementTasks()` ünite bazlı pekiştirme üretemiyor.
- **Classifier yazıldı ama çalıştırılmadı**: `scripts/source-ingestion/classify_exam_topics.py`
  (yeni) — Evren `laya` modeli ile `/v1/systemone` endpoint'inden konu tahmini. Pilot
  (12 soru, Türkçe Q01) çalıştı ve doğru dönüyordu (SÖZCÜKTE ANLAM), fakat 1080 soru
  henüz sınıflandırılmadı. `EVREN_API_KEY` env'de var. `BATCH=8, max_workers=4` ile
  çağrılabilir.
- AI'sız kural tabanlı H1-H7 sınıflandırıcı ve Supabase kurulumu hâlâ sırada (QBANK işi).

## Next Steps
1. Aylık deneme sorularına `topic`/`unit` eşlemesi yap → aylık deneme de pekiştirme üretsin.
2. Kullanıcı onayı: push/deploy yapılmadı (Product Owner yetkisi gerekli).
3. QBANK tarafı: kural tabanlı H1-H7 sınıflandırıcı + Supabase kurulumu.
