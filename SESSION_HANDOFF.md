# SESSION HANDOFF — 2026-11-05
**Canlı:** https://lgskanka.alibey.workers.dev (Version ID `bb689c9a-4efe-4c78-8453-1b0a268ee969`) | **Son push:** `e151d76` (main)

## 2026-11-09 — Haftalık test arşivi + aylık denemeler kapanmıyor + sonuç odaklı günlük plan

- **Haftalık test artık arşiv:** cumartesisi gelmiş her hafta açık kalır, geçmiş haftalar kapanmaz (hasta/müsait olmayan öğrenci sonradan çözer); gelecek hafta kilitli. `lib/cycle.ts` → `weeklyTestWeeks()`, `openWeeklyTestWeeks()`, `hasUnfinishedWeeklyTest()`, `dayKey()`, `weekKey()` (yerel gün, `toISOString` değil). Kayıt/seviye tespiti tarihinden önceki haftalar üretilmez; 4. hafta (aylık deneme) haftalık listeye girmez.
- **Haftanın soruları dondurulur:** yeni `lib/weekly-test-sets.ts` (`lgs_weekly_test_sets`, hafta anahtarı = cumartesi `YYYY-MM-DD`). Önceden her açılışta havuzdan yeniden seçildiği için "önceki haftanın testi" diye bir şey yoktu. Kompozisyon `activeWeek.saturday` referansıyla kurulur (o haftanın yanlışları).
- **`/haftalik-test/` UI:** hafta seçici eklendi (tarih · hafta no · ✓ Çözüldü / Çözülmedi / Kilitli), çözülmemiş en yeni hafta otomatik açılır, sonuç ekranında da seçici var. `/calis/` "Haftalık Teste Geç" butonu kaçırılmış hafta varsa açık kalır.
- **Aylık denemeler:** kilit yalnızca alt sınır (`monthsDiff >= month`) — süresi geçen ay kapanmıyor; ekrana not eklendi.
- **Kritik hata bulundu ve düzeltildi:** `lib/weekly-test.ts::composeWeeklyTest` soruları iç diziye ekliyordu (`items.push(...items)`), dış dizi hiç dolmuyordu → fonksiyon her zaman **0 soru** döndürüyordu. Ölçüm: `composed: 0` → düzeltme sonrası `composed: 45` (Tr/Mat/Fen 10, İnk/Din/Eng 5).
- **Sonuç odaklı günlük plan (önceki tur):** `lib/daily-plan.ts::composeDailyPlan` + `/calis` geniş havuz (`limit+10`) → son 3 günün yanlış üniteleri öne alınır, ders kotası korunur; `weakUnitsForPlanning(records, 3, excludeToday=true)` ile bugünün kayıtları planı kaydırmaz.
- **Pekiştirme (önceki tur):** `computeWeakUnits` iki kural — ünite 3+ yanlış VEYA son değerlendirme gününde ders <%60 ve ≥2 yanlış; `tamamlandi` görev sonraki yanlışta yeniden açılır, `servedQuestionIds` ile aynı soru tekrar atanmaz.
- **Doğrulama:** `npx tsx scripts/test-weekly-archive.ts` 11/11, `scripts/test-reinforcement.ts` 7/7, API sözleşme 29/29, taxonomy 4/4, `tsc`, `npm run build`, `npm run cf:build` geçti; yerel `/haftalik-test/`, `/aylik-denemeler/`, `/calis/` HTTP 200.
- **Yayın:** commit/push `e151d76` (remote eşleşti), deploy Version ID `bb689c9a-4efe-4c78-8453-1b0a268ee969`. Canlı `/`, `/calis/`, `/haftalik-test/`, `/aylik-denemeler/`, `/pekistirme/`, `/sonuclar/` HTTP 200. Canlı JS doğrulaması: `0ro3xlr0c9mav.js` içinde "Çözemediğin haftalar kapanmaz", `0zy_dos6vmw-c.js` içinde "Geçmiş ayların denemeleri kapanmaz", `0m_8ccel1xodm.js` içinde `+10}&sort=unit_difficulty` (geniş havuz) ve `servedQuestionIds` bulundu.

## 2026-11-09 — Seviye Tespit bozuk soru görselleri (4 adet)

- Kullanıcı `public/exams/00_seviye_tespit/` altındaki dört bozuk soru görselini (turkce Q08, turkce Q11, inkilap-tarihi Q04, inkilap-tarihi Q10) kaynak PDF'lerden kendisi kırpıp aynı adla değiştirdi. Kaynak yerleri: 2016 Sözel s.5 (Tr 8, sol sütun), s.7 (Tr 11, sol sütun), s.11 (İnk 4, sol sütun); 2017 Sözel s.14 (İnk 10, sağ sütun).
- `public/exams/` `.gitignore` içinde olduğundan bu PNG'ler Git'e girmez; görselleri deploy paketi taşır. `npm run build` + `npm run cf:build` + `wrangler deploy` çalıştırıldı; yükleme çıktısı dört PNG'yi "new or modified static asset" olarak listeledi.
- Deploy Version ID `6dca6d32-8c8d-4ab9-989b-ffe3d92caec9`. Cevap anahtarları değişmedi (Tr Q08 → B, Tr Q11 → B, İnk Q04 → B, İnk Q10 → D).

## 2026-11-05 — Pekiştirme görev görünümü (in-app yorumlar 6–7)

- `/pekistirme/` içindeki üç sayımlı özet kartı kaldırıldı. Ders düğmesi seçilince o dersteki ilk açık görev ve ilk cevaplanmamış soru açılır; soru görünümü çalışma sayfasındaki büyük soru/görsel/şık akışını kullanır, cevap sonrası “Sonraki soru” ile ilerler.
- Doğrulama: API sözleşme 25/25, taxonomy 4/4, `npm run lint`, `npm run build`, `npm run cf:build` başarılı; yerel ve canlı `/pekistirme/` HTTP 200. Canlı JS içinde “Sonraki soru” ve “Görevi tamamla” bulundu, kaldırılan `pekiştirme-summary` bulunmadı. Commit/push `eba4dd0`; deploy Version ID `551be78e-e1a3-4006-8b92-1203a1f81e35`.

## 2026-11-05 — Günlük sonuç adımları butonları (in-app yorum)

- `/calis/` sonuç kartındaki yönlendirme bağlantıları küçük butonlara dönüştürüldü: "Pekiştirme çalışması yap", hafta sonu "Haftalık test/Aylık deneme", "Sonuçlar ve İlerleme". Sadece `.next-steps` içindeki bağlantı görünümü değişti; hedef URL'ler ve çevreleyen metin korundu.
- Doğrulama: API sözleşme 25/25, taxonomy 4/4, TypeScript, Next.js ve Cloudflare build geçti; `/calis/` yerel HTTP 200. Commit/push `39c0022` (remote eşleşti); deploy Version ID `50225fb5-c248-4ab2-8b52-d998b97bdbbd`. Canlı `/calis/` HTTP 200; JS chunk `0uvbf02f-rozc.js` içinde metin/class, CSS `0ii24pesxbe9p.css` içinde buton kuralı doğrulandı.

## 2026-11-05 — Pekiştirme görev soruları açılabilir yapıldı (in-app yorum)

- Kullanıcı: "soru 1 bekliyor diyor soru 2 bekliyor diyor ama bu sorular nerede, üstlerine basınca bir şey çıkmıyor". Kök neden: `QuestionMini` ölü bir satırdı (yalnız "Soru N · Bekliyor" etiketi) — soru görseli, cevap şıkları ve tıklama hedefi hiç yoktu; `handleAnswer` hiçbir butona bağlı değildi.
- Düzeltme (`app/pekistirme/page.tsx`): soru satırına tıklayınca gerçek soru açılıyor — `.exam-question-image` görseli, büyütme overlay (ESC ile kapanır), "⚠ Soru eksik veya bozuk" bildirim butonu, A/B/C/D şıkları (`handleAnswer`'a bağlı). "Başla/Çözmeye Devam Et" ilk cevaplanmamış soruyu açar; 5 soru bitince görev `tamamlandi` olur. Görev görselleri `/api/study` havuzundan kimlikle eşleştirilerek yüklenir (eski görevler dahil).
- Doğrulama: API sözleşme 24/24, taxonomy 4/4, lint, Next + Cloudflare build geçti. Commit/push `e3cd7d8`; deploy Version ID `b6549692-9b2b-45b5-b490-aa7fc8a83deb`. Canlı `/pekistirme/`, `/calis/`, `/sonuclar/` HTTP 200; canlı JS chunk'ında yeni kod (`1dqtwpclh_r_l.js`) doğrulandı.

## 2026-11-05 — Günlük özet + pekiştirme düzeltmeleri (in-app yorumlar)

- **Günlük özet "0 doğru / 0 yanlış / 24 boş" kök nedeni:** sayfa yenilenince `/api/study?fresh=1` çözülen soruları eler; özet eski cevap kayıtlarını yeniden çekilen FARKLI soru kimlikleriyle eşleştirince 0 kayıt bulup tüm planı "Boş" sayıyordu. Düzeltme (`app/calis/page.tsx`): özet bugünkü `gunluk` cevap kayıtlarını soru başına tekilleştirerek sayar, `total = Math.max(questions.length, answered)`, `lgs-answer-records-changed` olayında (hidratasyon dahil) yenilenir.
- **Pekiştirme "henüz pekiştirme oluşmadı" kök nedeni:** `lib/reinforcement.ts` `detectWeakUnits` eşiği `subject|unit|topic` bazında uyguluyordu ve `topic: null` kayıtları tamamen atlıyordu. Düzeltme: eşik ünite bazında ("bir ünitede 3+ yanlış"), topic yalnızca görüntüleme etiketi (en sık yanlışlanan konu); ünite bilgisi olmayan kayıtlar uydurulmadan atlanır; `pekistirme` kayıtları tetikleyici sayılmaz.
- **Doğrulama:** API sözleşme 23/23, taxonomy 4/4, `npm run lint`, `npm run build`, `npm run cf:build` geçti. Commit/push `e8cd94e` (remote eşleşti); deploy Version ID `01e91491-5a2e-4c13-aa42-47b2811baeb9`. Canlı `/calis/`, `/pekistirme/`, `/sonuclar/` HTTP 200; canlı JS chunk'ında yeni kod (`0eqka9d47djg7.js`) doğrulandı.
- Commit'e alınmayanlar (bilinçli): `AGENTS.md` (araç yazımı marker değişikliği), `update-check/wrangler-latest.json` (makine önbelleği), `.ses/`, `data-gym-cache/`, `scripts/output/` (kullanıcı verisi/çöp).

## 2026-11-04 — UI düzeltmeleri (in-app yorumlar)

- Günlük sonuç kartı aynı günkü `gunluk` cevap kayıtlarını mevcut soru havuzunun ID'leriyle eşleştirmeden hesaplıyor ve `lgs-answer-records-changed` olayında yenileniyor; bu düzeltme canlıda.
- Yorumlar için yapılan değişiklikler deploy edildi: aylık deneme sonucu etiketi `Net (yaklaşık)` oldu; ana sayfa Derslerim kartları `computeSubjectAccuracy()` ile gerçek cevap kayıtlarından hesaplanıyor, veri yoksa "Henüz yanıt yok" gösteriyor; Pomodoro kartı, güncel döngüyle uyumsuz 45 soruluk hedef barı ve "Bugünün görevleri" demo kartı kaldırıldı.
- Comment 7 denetimi ve düzeltmesi: hata sayıları gerçek, sınıflandırılmış yanlış cevap kayıtlarından türetiliyor; H1–H7 görünen adları canonical `errorTypes` kaynağından üretiliyor ve sonuç sayfası hidratasyon/yeni cevap olaylarında yenileniyor. Deploy edildi.
- **Canlı hesapta görülenler:** hitap adı `ali` olan (kullanıcı tarafından `lgsdeneme` hesabıyla aynı olduğu doğrulandı) hesapta `/sonuclar/` 25 cevap kaydı, 9 doğru, 16 yanlış, 10/16 sınıflandırılmış; H1=6, H2=3, H3=1. Günlük özet 24 soru ve 9 doğru. `/sonuclar` tüm kaynak kayıtlarını; günlük özet bugünkü `gunluk` kayıtlarını soru başına tekilleştirerek sayar. 25. kaydın tam kaynağı UI'dan/aktif browser kontrolüyle henüz doğrulanamadı.
- **Sınıflandırma kök nedeni/düzeltme:** `app/calis/page.tsx` içindeki "Konuyu bilmiyorum" seçeneği `code: null` idi; seçim yapılmış olmasına rağmen sınıflandırılmıyordu. H1 olarak düzeltildi ve deploy edildi. Daha önce kaydedilmiş `null` kayıtlar neden seçiminin kimliğini taşımadığından otomatik geriye dönük sınıflandırılamaz.
- **Sayı gösterimi:** Ana sayfa ders kartları, devam kartı, günlük özet, haftalık/aylık deneme ve sonuç ekranları `Doğru / Yanlış / Boş / Toplam` etiketlerini kullanıyor; günlük toplam mevcut soru havuzuyla sınırlı tutuluyor. Geçmiş kayıtlarda boş adedi bilinmiyorsa `—` gösteriliyor.
- **Doğrulama:** API sözleşme 20/20, taxonomy 4/4, `npm run lint`, `npm run build`, `npm run cf:build` geçti. Canlı `/`, `/calis/`, `/aylik-denemeler/`, `/haftalik-test/`, `/sonuclar/` HTTP 200; canlı JS'de dört etiket doğrulandı. Deploy Version ID `e5d3138a-8cbb-4129-9d37-2f3e4afc725e`; commit/push `626be60`.

## 2026-11-04 — Oyun süresi ve çıkış yeri (in-app yorumlar)

- Oyun hakkı eşiği 20 XP'de 5 dakika, 50 XP'de 8 dakika, 100 XP'de 10 dakika oldu; günlük üst sınır 10 dakika / 2 oturum olarak korundu. Ödüller sayfasındaki açıklamalar güncellendi.
- Masaüstünde çıkış düğmesi sol menünün altına taşındı; dar ekranlarda profil sayfasında kaldı çünkü sol menü gizleniyor.
- Doğrulama: lint, API sözleşme 22/22, taxonomy 4/4, Next.js build, Cloudflare build başarılı. Canlı `/oduller/` ve `/profil/` 200; yüklenen JS/CSS'de güncel oyun süresi ve çıkış kontrolleri bulundu. Commit/push `0f7a9a9`; Version ID `0c662175-46cd-4d4a-989c-8e369eeb08ed`.

---

## 2026-11-04 — Güvenlik ve çalışma sonuçları düzeltmeleri (canlıya dağıtıldı: `83977869-bc00-454f-b2a3-c6743d7625e3`)

Kullanıcı tüm düzeltmelerin sırayla yapılmasını onayladı. Bu oturumda çalışma alanına uygulananlar:
- `/api/study` cevap anahtarını hiçbir GET modunda döndürmüyor; POST kimlik doğrulamalı ve kullanıcı/IP başına 120/dk rate limitli. Günlük, haftalık ve pekiştirme istemcileri `apiFetch` kullanıyor.
- `/api/exams-submit` kimlik doğrulamalı, öğrenci kimliğini token'dan alıyor, aynı ay/deneme tekrarında kayıtlı sonucu döndürüyor ve public details'tan answer key çıkarıyor.
- `/api/answer-records` doğruluğu kanonik soru anahtarından hesaplıyor; hata kodu, kaynak ve soru metadata'sını sınırlandırıyor. Kayıtlar akış kaynağına (`gunluk`/`haftalik`/`pekistirme`) göre ayrılıyor.
- `/api/profile` sahiplik kontrolü GET/POST/DELETE'e eklendi. Güvensiz kullanıcı adıyla parola sıfırlama kapatıldı (410); UI öğretmene yönlendiriyor.
- Günlük sonuç özeti yalnızca bugünkü kayıtlı günlük cevapları sayıyor; sonuç beklenirken ilerleme kapalı, kayıt sayısı ayrıca gösteriliyor.
- Rozet ve istatistikler dizi/nesne localStorage biçimlerini destekliyor ve cevap/hidratasyon olaylarında yeniden hesaplanıyor.
- Manifest üretimi yalnızca `VERIFIED` + `published=true` girdileri kabul ediyor; boş/uygunsuz manifest yayınlamayı reddediyor.
- `lgs-coach-app` skill'deki eski cevap anahtarı ve parola kurtarma talimatları güncellendi.

**Doğrulama:** `npm run lint` ✅; `npm run build` ✅ (Next middleware→proxy deprecation uyarısı); `npm run cf:build` ✅; `npx wrangler deploy --dry-run` ✅; Python source-ingestion 109/109 ✅; API sözleşme 15/15 ✅; taxonomy 4/4 ✅.
Canlı smoke (browser UA): `/calis/` 200; `/api/study` toplam 5034 soru (dersler: Türkçe 1486, Matematik 1338, Fen 905, İnkılap 438, Din 434, İngilizce 433), cevap anahtarı alanı 0; kimliksiz study/answer-records/exams-submit POST 401; forgot POST 410; yeni görsel 200. Wrangler deploy sonucu version `83977869-bc00-454f-b2a3-c6743d7625e3`.

**Supabase:** Bu deploy için yeni DDL çalıştırılmadı. Kanonik `supabase/schema.sql` içinde `answer_records.source` alanı ve `(student_id, question_id, source)` unique kısıtı zaten tanımlı. Canlı öğrenci hesabıyla yazma testi yapılmadı; eğer bu şema canlı Supabase'e henüz uygulanmadıysa bu kısıtların uygulanması gerekir.

**Kaynak ve görsel staging:** Doğru resmî PDF `scripts/source-ingestion/data/questions/archive/MEB-LGS-2022/01-2022_sayisal_bolum_a_kitapcigi_ve_cevap_anahtari.pdf` içindeydi; SHA-256 kayıtlı `8a1c6526...` ile eşleşti. Kullanıcının `kaynak dosyalar/Lgs_soruları/Lgs_2022` klasöründeki matematik/fen PDF'leri ayrı dosyalar. Doğrulanmış arşiv PDF'iyle görsel staging yeniden üretildi; eksik Matematik Q10/Q11/Q12/Q14, ana staging'deki değişmemiş kayıtlar olarak geri eklendi. `repair_structural_gate.py` R10 dışındaki kayıtları koruyor; test, repaired kayıt kümesini kaynak kayıt kümesiyle karşılaştıracak şekilde düzeltildi. İki görsel soru `NEEDS_REVIEW`, `published=false`; hiçbiri VERIFIED yapılmadı.

**Yayın/diğer:** Canlı dağıtım tamamlandı; Git commit/push yapılmadı. `AGENTS.md` değiştirilmedi (önceki araç onay engeli nedeniyle tekrar denenmemeli). `.ses`, `data-gym-cache/`, `scripts/output/` untracked öğelerine dokunma; kullanıcı verisi olabilir. Güvenli self-service parola kurtarma ayrıca tasarlanmalı.

---

## 2026-11-03 — Haftalık test + rozet kalıcılığı (sunucuya taşıma) — TAMAMLANDI

**Kullanıcı talebi:** "Haftalık test geçmişi tablosu ve rozet ilerlemesi sunucuda tutulmadığı için çıkışta siliniyor — onları da sunucuya taşı."

**Mevcut durum:**
- `badge_progress` tablosu şemada VAR (şema `supabase/schema.sql` L107-115) ama kod localStorage (`lgs_badge_progress`) kullanıyordu — sunucuya yazılmıyordu.
- `weekly_test_history` tablosu YOK — eklenmeli.
- `lgs_streak` yazılmıyordu — seri rozetleri (4 Gün, 7 Gün, Hedefe Sadık) asla kazanılmıyordu.

**Çözüm (commit `3bf9b3a`, canlı Version `ee716cd4`):**

1. **DDL (siz Supabase Dashboard > SQL Editor'de çalıştıracaksınız):**
```sql
create table if not exists weekly_test_history (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references students(id) on delete cascade,
  date timestamptz not null,
  total int not null,
  correct int not null,
  wrong int not null,
  blank int not null,
  by_category jsonb not null default '{}',
  weak_units jsonb not null default '[]',
  question_ids jsonb not null default '[]',
  wrong_question_ids jsonb not null default '[]',
  created_at timestamptz not null default now()
);
create index if not exists idx_weekly_test_history_student
  on weekly_test_history (student_id, date desc);
alter table weekly_test_history enable row level security;
```
(`badge_progress` zaten şemada var; tekrar oluşturmaz.)

2. **API: `/api/progress` (GET/POST type=badges|weekly_tests)** — `reinforcement-tasks` pattern, auth-scoped.

3. **Sync helpers (`lib/sync.ts`):** `pushBadgeProgress`/`pullBadgeProgress`, `pushWeeklyTestHistory`/`pullWeeklyTestHistory` (fire-and-forget).

4. **Hydration (`profile-provider.tsx` → `hydrateMirrors`):** Girişte sunucudan rozet/haftalık çekip `lgs_badge_progress` + `lgs_weekly_test_history` localStorage'a yazar.

5. **Haftalık test bitiş:** `saveWeeklyTestRecord` → `pushWeeklyTestHistory` fire-and-forget.

6. **Rozetler:**
   - Seri kaynağı düzeltildi: `computeLearnerStats().streakDays` (sunucu kayıtlarından) → 4/7 Gün Seri rozetleri artık kazanılabiliyor.
   - `data/content.ts` badge defaults `earned: false` (sunucu/kayıtlardan hesaplanır).
   - `useBadgeProgress` mount'ta kazanan rozetleri sunucuya yaz (`pushBadgeProgress`).

7. **Kalıcılık garanti:** Çıkışta yerel temizlense bile, yeniden girişte `hydrateMirrors` → sunucudan rozet/haftalık/deneme geçmişi/döngü anchor/kayıt tarihi geri yüklenir.

**DDL çalıştırıldı (2026-11-03):** Kullanıcı Supabase Dashboard → SQL Editor'da tabloları oluşturdu ✅. İlk denemede `ON CONFLICT (student_id, date)` hatası çıktı (42P10) — `unique (student_id, date)` kısıtı eklenerek düzeltildi ✅. `supabase/schema.sql` kanonik kopya güncel.

**Canlı doğrulama (hersstest4):** rozet yaz/oku (2 rozet) ✅ · haftalık test yaz → aynı tarihli tekrar yaz (upsert güncelleme, 31/45) ✅ · token yok → 401 ✅ · yeniden giriş → kayıt duruyor ✅

**Test:** Canlı headless Chrome — çıkış/geri giriş akışı, rozet/haftalık endpoint 401/empty, continuation done=true ✓

---

## 2026-11-03 — "Çıkış yap" butonu (`3b65bba`)

**Kullanıcı raporu:** Tarayıcı geçmişi/çerezleri silinse bile aynı profil açılıyordu (localStorage `lgs_token` çerezlerden bağımsız) → yeni giriş yapılamıyordu.

**Çözüm:**
- `/profil` → "Öğrenci bilgileri" kartı → **"Hesap"** bölümüne **"Çıkış yap"** butonu (onay diyaloğu).
- `logout()` artık öğrenciye özel yerel anahtarları temizliyor: `lgs_answer_log`, `lgs_reinforcement_tasks`, `lgs_exam_history`, `lgs_weekly_test_history`, `lgs_completed_exams`, `lgs_cycle_anchor`, `lgs_enrollment_date`, `lgs_badge_progress`, `lgs_streak`, `lgs-ai-coach-tasks`, `lgs-ai-coach-game-session`, `lgs-ai-coach-pomodoro-v1`. (Temizlenmezse sonraki öğrenci öncekinin verilerini görüyor + eski kayıtlar hydrateMerge ile yeni hesaba push'lanıyordu.)
- Girişte geri yükleme (yerel temizlense/cihaz değişse de): `/api/exams-status` → tamamlanan aylar + deneme geçmişi; month 0 `completedAt` → `setCycleAnchor`; `student.registeredAt` → `setEnrollmentDate` (hem login() hem sayfa açılışı).
- Bilinen kayıp: haftalık test geçmişi + rozet ilerlemesi sunucuda YOK — çıkışta silinir, geri gelmez (rozetler cevap kayıtlarından yeniden hesaplanır).

**Doğrulama (canlı headless Chrome):** buton ✓ · çıkış sonrası tüm anahtarlar temiz + giriş formu ✓ · yeniden girişte anchor `2026-11-03T08:57:54Z`, `exam_history` 1 kayıt, `completed_months [0]`, enrollment = registeredAt ✓

---

## 2026-11-03 — In-app yorumlar (3 madde) — TAMAMLANDI

### 1) Yorum 2: "Hata türü dağılımı" kartı sabit, hiç değişmiyor
**Kök neden:** `/api/study` her gün aynı 24 soruyu (deterministik `unit_difficulty` sıra) servis ediyordu + `answer_records` soru başına tek kayıt (upsert) → re-answered questions overwrite → kayıtlar büyümez, H-distribution donuyor ("5 hata · %42" günlerce aynı).

**Çözüm:**
- `GET /api/study?fresh=1` → son 30 günde çözülen sorular (answer_records.question_id) hariç tutulur, taze sorular önce gelir; havuz tükenirse tekrarlar geri döner.
- `/calis` fetch → `apiFetch(...&fresh=1)` (Authorization header gönderir).
- Sonuç: her gün yeni 24 soru → yeni kayıtlar → H-distribution her gün değişir.

### 2) Yorum 3: "Denemeler her ay bir, cumartesi" → kopya düzeltmesi
- `app/aylik-denemeler/page.tsx:630` — "ayda bir, cumartesi" olarak düzeltildi.

### 3) Yorum 4: "Seviye 4 hala sabit görünüyor" (TopBar + /profil + /oduller)
**Kök neden:** `data/nav.ts`'teki `learner` tamamen demo veri (`xp: 245`, `streakDays: 4`, `levelXp: 145`, `levelTarget: 320` sabit) — `level` getter XP'den hesaplansaydı da XP sabit → herkes Seviye 4.

**Çözüm — `lib/learner-stats.ts` (yeni):**
- `computeLearnerStats()` → `loadAnswerRecords()` üzerinden:
  - XP = doğru × 2 (aynı kural `/calis` DailySummary: "doğru başına 2 XP").
  - Streak = bugün/dünden geriye doğru kesintisiz günler (UTC tarih).
  - Seviye eşikleri: `[0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200]` (kümülatif XP).
  - `levelXp` = XP - mevcut eşik; `levelTarget` = sonraki eşik - mevcut eşik.
- `useLearnerStats()` hook: mount'ta hesaplar, öncesi `null` (SSR uyumlu — hydration mismatch yok).
- Tüketiciler (hook + `?? learner.*` fallback):
  - `components/chrome.tsx`: `TopBar` (streak, XP, level, levelXp/levelTarget, çubuk) + `Sidebar` greeting.
  - `app/page.tsx`: Home "Kazanımlarım" streak kartı.
  - `app/profil/page.tsx`: "Karakter durumu" (Seviye pill, XP, streak) + unlockables "Seviye ödülleri".
  - `app/oduller/OdullerClient.tsx`: XP kartı.

**Doğrulama:**
- `npm run lint` ✅ · `npm run test:taxonomy` 4/4 ✅ · `npm run build` ✅ · `opennextjs-cloudflare build` ✅ · `wrangler deploy` ✅ (Version `0ebcc80f`).
- Canlı:
  - 6 sayfa HTTP 200.
  - Kopya "ayda bir" (JS sonrası görünür).
  - TopBar `/api/continue`: done=true, 24/24, completed=true.
  - Rotasyon: `fresh=1` endpoint hersstest2 için farklı soru IDs döndürüyor.

**Bilinen/uncommitted:** `.ses`, `data-gym-cache/`, `scripts/output/` yanlışlıkla commitlendi — temizlenmeli.

---

## ✅ ÖNCEKİ ACİL TAMAMLANDI (2026-11-03 ikinci oturum)

Yerel değişiklikler commit + push + deploy edildi (`dd9857e`):
1. ✅ `git add` + commit + `git push origin main` → `54ce75f..dd9857e`
2. ✅ `npm run lint` ✅ · `npm run test:taxonomy` 4/4 ✅ · `npm run build` ✅ · `opennextjs-cloudflare build` ✅ · `wrangler deploy` ✅
3. ✅ Canlı doğrulama: 4 sayfa 200, `GET /api/exams-status` 200 + `{completedMonths, results}` şekli, canlı chunk'ta `exams-status`/`Tamamlandı` stringleri (taze build kanıtı)
4. ⚠️ KALAN: @lgsdeneme1 hesap girişi doğrulanamadı — şifre standart `1234` değil. Kullanıcı son kontrolü kendisi yapacak (veya şifreyi verirse / sıfırlama onaylarsa ajan tamamlar)

---

## Bu Oturumda Yapılanlar (2026-11-03)

### 1. Karakter seviye kartı düzeltmesi
- Sorun: her kullanıcıya sabit "4. Seviye" gösteriliyordu (`data/nav.ts`'de `level: 4` sabit).
- Çözüm: `learner.level` → `gameEconomy.tiers`'ten XP'ye göre hesaplanan getter (maks 4).

### 2. "Biten deneme/çalışma hâlâ açık" hatası (kullanıcı raporu: @lgsdeneme1)
- **Kural (kullanıcı talebi):** "Herhangi bir deneme veya çalışma bittikten sonra sorular kapansın, sadece sonuç ve istatistikler görünsün."
- **Kök neden 1:** `/aylik-denemeler` tamamlanmayı sadece `localStorage["lgs_completed_exams"]`'ten okuyordu. Sunucu kaydı (Supabase `exam_results`) yok sayılıyordu → localStorage kaybında sınav "açık" görünüyordu (aynı sınıf hata @lgscep'te kapılar için çözülmüştü: `54ce75f`).
- **Kök neden 2:** Biten ay dropdown'da "✓" alıyordu ama pasifleşmiyordu; seçilince sorular + "▶ Süreyi Başlat" geri geliyordu.

**Çözüm:**
- **Yeni `GET /api/exams-status`** (`app/api/exams-status/route.ts`): girişli öğrencinin `exam_results` kayıtlarından tamamlanan aylar + özet sonuçlar (ay başı en yeni kayıt geçerli).
- **`app/aylik-denemeler/page.tsx`**: mount'ta sunucu kaydı localStorage ile birleştirilir; tamamlanan ay seçilirse sorular yüklenmez, sonuç ekranı gösterilir (öncelik: oturum sonucu → `lgs_exam_history` → sunucu `results`); geç gelen sunucu verisi, kullanıcı başlamadıysa (timerStarted=false + cevap yok) oturumu kapatıp sonucu gösterir; submit sonrası sadece sonuç; dropdown "✓ Tamamlandı".
- **`app/calis/page.tsx`**: `/api/study-session` cevabında `solved >= target` ise `completed=true`; `completed` iken soru bölümü + zoom overlay + "soru bulunamadı" gizli, sadece özet kart görünür.
- **`app/haftalik-test/page.tsx`**: mount'ta `loadWeeklyTestHistory()`'den bu haftanın cumartesi tarihli kaydı aranır; varsa `finished=true` + `savedRecord` ile sadece sonuç görünümü. Sonuç hesabı `results` (taze) veya `savedRecord` (geçmiş) ikisinden de çalışır şekilde refactored.

**Doğrulama:** `npm run build` ✅ · `npm run test:taxonomy` 4/4 ✅ · localhost:3000 sayfalar 200 ✅

---

## Geçmiş Oturum Özeti (2026-11-02 → commit `54ce75f`)

1. Haftalık Test Kapısı — `gateOpen` dependency eklendi
2. Pekiştirme Sayfası JSX — `</article>` Turbopack regex fix
3. Günlük Çalışma Kapısı — `levelTestDone` state + kilit ekranı
4. Mobil & Tablet Uyumluluk — safe-area, iOS zoom engelleme, 44px dokunma hedefleri
5. Cloudflare Error 1102 CPU Limit — per-subject manifestolar (346KB-1.5MB)
6. Ücretsiz Katman Koruması — 500 öğrenci + rate limit
7. Seviye Tespit Kapısı Sunucu Doğrulama — `/api/level-test-status` + Supabase fallback

---

## Teknik Mimari (kısa — detay eski commitlerde)

```
lgskanka.alibey.workers.dev
├── /api/auth/register|login  → Supabase students + JWT + 500 sınırı + rate limit
├── /api/level-test-status    → Seviye tespit durumu (Supabase fallback)
├── /api/exams-status         → YENİ: tamamlanan aylar + özet sonuçlar
├── /api/study                → Per-subject manifestolar (R2 binding)
├── /api/exams-submit         → Sınav değerlendirme + exam_results kaydı
└── /r2/[...key]              → R2 görsel proxy
```

### R2 / veri
- 5,170 WebP görsel + 6 per-subject manifest (`questions_{subject}.json` ×6 AKTİF; `all_questions.json` KULLANMA)
- Supabase tabloları: students, exam_results, exam_sessions, study_sessions, answer_records, question_reports

---

## Önemli Pitfall'lar (deploy için — hâlâ geçerli)

| # | Pitfall | Çözüm |
|---|---------|-------|
| 1 | `wrangler r2` yerel `.wrangler/state`'e yazar | `--remote` flag ekle |
| 2 | `next build` sonrası `opennextjs-cloudflare build` zorunlu | Yoksa JS chunk'ları kopyalanmaz |
| 3 | Per-subject manifestolar CPU limit aşımını çözdü | `all_questions.json` KULLANMA |
| 4 | Deploy sırası: `npm run build` → `opennextjs-cloudflare build` → `wrangler deploy` | Sıra önemli |
| 5 | Turbopack JSX parser `</tag>` → regex | Closing tag'lere attribute ekleme |
| 6 | Rate limit per-isolate in-memory | Restart'ta sıfırlanır |

---

## Bilinen Eksikler / Sonraki Adımlar

| # | Görev | Öncelik |
|---|-------|-------|
| 1 | ~~Yerel değişiklikleri push + deploy~~ → TAMAM (`dd9857e`, 2026-11-03) | ✅ |
| 2 | @lgsdeneme1 ile canlı sonuç ekranı son kontrolü (şifre gerekli) | Orta |
| 3 | Haftalık test "bitmiş" kontrolü sadece localStorage'da (localStorage kaybında yeniden açılır — ileride sunucu fallback eklenebilir) | Düşük |
| 4 | P3 kişiselleştirme UI kartı (`/sonuclar-ve-ilerleme`) | Orta |
| 5 | Aylık deneme `topic`/`unit` null sorunu (1080 soru sınıflandırılmadı) | Orta |
| 6 | `lgs_çalışma_soruları` PNG entegrasyonu | Düşük |

---

## Kullanıcı Tercihleri
- Türkçe, kısa ve direkt yanıt
- Non-developer, GUI öncelikli, onay al kodu yaz
- Ücretsiz katman aşılmasın (500 öğrenci sınırı)
- ~50 sınıf arkadaşı, ticari değil
- AI tamamen iptal — H1-H7 kural tabanlı
- §20 Karakter: avatar/profile var; 3D/aksesuar/oda YOK (sistem yükü)