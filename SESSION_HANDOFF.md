# SESSION HANDOFF — 2026-11-03
**Son commit (push edilmiş):** `3b65bba` | **Canlı:** https://lgskanka.alibey.workers.dev (Version ID `15dd39da-1d7e-4a18-a878-c919b5e16532`)
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