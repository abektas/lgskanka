# TASK-QBANK-001 — Question Bank v2 Foundation

**Tarih:** 2026-10-03
**Görev:** Issue #5, `TASK-QBANK-001`
**Kapsam:** Yalnız veri modeli / migration / test foundation

## 1. Sonuç

`questions` ve `question_sources` tablolarına **dokunulmadan**, geriye dönük
uyumluluğu bozmadan 15 yeni tablo eklendi. `/api/questions` değiştirilmedi,
production davranışına dokunulmadı.

## 2. Değişen dosyalar

| Dosya | Değişiklik |
|---|---|
| `db/002_question_bank_v2.sql` | YENİ — migration (15 tablo, 2 trigger, 10 index) |
| `db/002_question_bank_v2.down.sql` | YENİ — rollback |
| `tests/db/run_question_bank_v2_tests.sh` | YENİ — gerçek PostgreSQL'e karşı 24 test |

Mevcut hiçbir dosya değiştirilmedi.

## 3. Oluşturulan tablolar

**Curriculum:** `curriculum_layers` · `subjects` · `units` · `topics` ·
`learning_outcomes` · `skills`
**İlişki:** `question_topics` · `question_skills` · `question_learning_outcomes`
**Pedagogy:** `error_types` (referans) · `question_pedagogy` ·
`question_secondary_error_types`
**Zorluk:** `question_difficulty`
**İlişkiler:** `question_relations`
**Kalite:** `question_quality`

## 4. Constraint / index özeti

**CHECK:** confidence 0–1 · difficulty boyutları 0–1 · relation type enum ·
self-relation yok · tek birincil eşleşme (kısmi unique index) ·
review tutarlılığı · pedagogy boş olamaz · difficulty/assessment tutarlı

**UNIQUE:** `(question_id, …)` çiftleri · aynı ilişki iki kez yazılamaz ·
katman+subject+unit adı tekil

**FK:** tüm question→topic/skill/outcome/pedagogy/quality bağları `on delete cascade`

**Trigger (2):** ikincil hata birincil ile aynı olamaz — iki yönde de
(ikincil eklenirken ve primary değişirken)

**Index (10):** adaptive selector ters yönleri, curriculum hiyerarşisi,
kalite durumu, zorluk sıralaması

## 5. Test sonuçları (gerçek PostgreSQL 16)

```
bash tests/db/run_question_bank_v2_tests.sh --local-test-container
→ geçen: 24   kalan: 0   (EXIT=0)
```

Kapsanan: migration uygulanabilirliği · idempotency · 17 tablo · 001 verisi
etkilenmemiş · H9 reddi · difficulty aralık · confidence aralık · self relation ·
geçersiz relation type · geçerli kayıtlar · ikinci birincil reddi · duplicate
relation · ikincil=birincil reddi (her iki yön) · FK bütünlüğü · curriculum
katman ayrımı · quality review tutarlılığı.

| Komut | Sonuç |
|---|---|
| `npm run test:watcher` | 33/33 |
| `npm run test:source` | 3/3 |
| `npm run test:taxonomy` | 5/5 |
| `npm run validate:sources` | OK — 6 resmi kayıt |
| `npm run build` | EXIT=0 |
| `git diff --check` | temiz |

## 6. Rollback

`db/002_question_bank_v2.down.sql` doğrulandı: 17 tablo → 2 tablo
(`questions`, `question_sources` korunur). Yalnız 002'den sonra yeni kayıt
girilmemişse güvenlidir.

## 7. PENDING — karar bekleyen konular

1. **`cognitive_level` serbest metin.** Bloom gibi bir kademe taksonomisi
   bağlayıcı kaynaktan tanımlı değil; sözlük tablosu eklemek mimari karar
   gerektirir. Şimdilik CHECK kısıtı yok.
2. **Immutable revision tablosu EKLENMEDİ.** Görev "temel oluştur" dedi;
   soru geçmişi tablosu ayrı bir karardır.
3. **`error_types` seed verisi.** Tablo boş; `data/content.ts → errorTypes`
   ile eşleşen 7 satır **application/ingestion sırasında** yüklenmeli.
   Doğrudan seed INSERT'i eklenseydi iki kaynaklı doğruluk kaynağı doğardı.
4. **`skills` katmana bağlı, `topics` üniteden.** Bilinçli: bir beceri çok
   konuya ait olabilir. İleride değişmesi gerekiyorsa migration 003 gerekir.

## 8. Out of scope — YAPILMAYANLAR

- ❌ `/api/questions` production davranışı değiştirilmedi
- ❌ JSON question store DB'ye taşınmadı
- ❌ Adaptive selector / student attempts / mastery / spaced repetition **yazılmadı**
- ❌ AI Question Factory / otomatik soru üretimi **yazılmadı**
- ❌ Gemini/OpenAI entegrasyonu **yazılmadı**
- ❌ Frontend / gamification / parent panel **değiştirilmedi**
- ❌ Auto merge / deploy **yapılmadı**

## 9. Bilinen riskler

- PostgreSQL `CHECK` kısıtı alt sorguya izin vermedi; ikincil/birincil
  ayrımı trigger ile uygulandı. Uygulama katmanı bunu atlamamalı.
- Test scripti `docker exec` kullanıyor; CI'da `TEST_DATABASE_URL` modu var.

## 10. Sonraki doğal görev

**TASK-QBANK-002:** `error_types` seed + ingestion entegrasyonu ve
curriculum içeriğinin doldurulması. Veri olmadan foundation tek başına
işe yaramaz; bu görev foundation'ı **kullanılabilir** hale getirir.