---
name: lgs-question-engine
description: Nüli (LGS AI Coach) soru bankası ve MEB kaynak güvenilirliği işleri için proje-özgü kurallar. Soru ekleme/publish etme, source provenance, canonical staging, VERIFIED geçişi, duplicate tespiti, curriculum mapping, MEB ingestion pipeline ve /api/questions sözleşmesi değişikliklerinde kullan.
---

# lgs-question-engine

Soru bankası + kaynak güvenilirliği çalışmalarının proje kuralları.

## Yetkili kaynak (tek doğruluk kaynağı)

**`AGENTS.md`** bu projenin sözleşmesidir. Aşağıdaki bölümler tekrar yazılmaz, atıf yapılır:

| Kural | AGENTS.md bölümü |
|---|---|
| Kaynak hiyerarşisi ve provenance | "Source policy and provenance" |
| İçe aktarma, hash, manifest, idempotency | "Ingestion, identity, and manifests" |
| Soru/cevap bütünlüğü, answer key sunucuda kalır | "Question bank and answer integrity" |
| Müfredat katmanları | "Curriculum layers" |
| Doğrulama durumları | "Question bank and answer integrity" |

Bu skill **operasyonel bilgiyi** (kanonik değerler, dosya→kural haritası, komutlar, tuzaklar) taşır. Bir çelişki görülürse kod değil AGENTS.md esas alınır ve çelişki raporlanır.

## Kanonik değerler (kodla doğrulanmış)

**Kaynak tipleri** (`validate_source_registry.SOURCE_TYPES`, `canonical_schema.json`, `db/001_question_bank.sql`):
`REAL_LGS`, `MEB_SAMPLE`, `MEB_BOOK`, `MEB_CURRICULUM`, `VERIFIED_EXTERNAL`, `AI_GENERATED`
→ gerçek liste koddan okunmalı; `AI_GENERATED` öneki `AI-` ile başlamak zorundadır ve MEB kaynağı gibi gösterilemez.

**Canonical staging'de yalnızca** `REAL_LGS` ve `MEB_SAMPLE` kabul edilir (`canonical_schema.json` → `source.source_type` enum).

**Yaşam döngüsü**: `DRAFT → EXTRACTED → AUTO_CHECKED → NEEDS_REVIEW → VERIFIED`, ayrıca `REJECTED`.
`VERIFIED` terminaldir; sadece `NEEDS_REVIEW` → `VERIFIED` geçişi mümkündür.

**11 zorunlu kontrol** (`REQUIRED_CHECKS`): `source_verified`, `year_verified`, `booklet_verified`, `question_number_verified`, `text_verified`, `options_verified`, `answer_key_source_verified`, `answer_key_verified`, `curriculum_verified`, `solution_verified`, `duplicate_checked`.
`answer_key_source_verified` ile `answer_key_verified` **ayrı** kapılardır; biri diğerini ikame etmez.

**Cevap anahtarı otoritesi = `OFFICIAL_MEB_ONLY`.** Extraction'ın bulduğu metin yalnızca *aday*dır; canonical `answer_key.answer` yalnızca resmî MEB anahtarından doldurulur.

**Müfredat**: kayıtta her iki katman da bulunur (`LGS_REFERENCE_2018_PLUS`, `CURRENT_TYMM`); en az biri kanıt bağlantısıyla `VERIFIED` olmadan yayın yok.

## Kural → kod haritası

| Kural | Nerede uygulanıyor |
|---|---|
| 2018 tabanı (REAL_LGS) | `scripts/source-ingestion/validate_source_registry.py`, `validate_canonical.py`, `db/001_question_bank.sql` |
| MEB/CDN host allowlist, redirect | `scripts/source-ingestion/source_trust.py` |
| Keşif + indirme + manifest | `download_official_pdfs.py`, `create_ingestion_manifest.py` |
| Aday çıkarımı (asla VERIFIED değil) | `extract_pdf_candidates.py` |
| Duplicate parmak izi | `build_review_queue.fingerprint` ← `validate_canonical.canonical_fingerprint` |
| Yayın kapısı | `validate_canonical.transition`, `publish_verified.publish` |
| API sözleşmesi (cevap gizli) | `app/api/questions/route.ts` + `tests/source-ingestion/api-contract.test.mjs` |

## Bu görevde çalıştırılacak komutlar

```sh
npm run validate:sources     # registry bütünlüğü (6 resmî kayıt beklenir)
npm run test:source          # 24 Python testi + 3 API sözleşme testi
python3 -m unittest discover -s tests/source-ingestion -v
```

`questions.json` boşsa bu normaldir: doğrulanmamış kayıt yayınlanmaz.

## Tuzaklar

- **Testi gevşeterek geçirmek yasak.** Önce gerçek kod problemini bul.
- `--booklet` verildiğinde kayıtsız kitapçık kodu veya eşleşmeyen anchor sessiz başarı üretmemelidir; hata verir.
- Manifest `archive_path` değerleri çalışma dizinine göre yazılır; kök `data/questions/...` bekleniyorsa `--archive-dir`/`--manifest-dir` açıkça ver.
- `.env.local` içeriğini okuma, raporlama veya loga alma.
- Cevap anahtarı/çözüm, öğrenci cevaplamadan önce client'a gönderilemez.
