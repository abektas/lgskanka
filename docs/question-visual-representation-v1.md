# Görsel soru temsili sözleşmesi v1 (canonical)

**Görev:** TASK-QBANK-005 (R9) · **Tarih:** 2026-10-05 · **Durum:** uygulanan sözleşmenin kaydıdır
(`canonical_schema.json` + `validate_canonical.py` + `publish_verified.py` +
`app/api/questions/route.ts` ile birebir; ikinci bir şema icat edilmez).

Bu belge `docs/question-ingestion-spec-v1.md` içinden referanslanır ve görsel-dominant
bir MEB sorusunun canonical kayıtta nasıl temsil edileceğini tanımlar. Genel boru hattı
kuralları (provenance, `VERIFIED` kapısı, cevap anahtarı gizliliği) spec'tedir; burada
tekrarlanmaz, yalnızca görsel temsile özgü sözleşme yazılır.

## 1. Temsil modları

`question.representation` opsiyoneldir (yoksa `STRUCTURED_TEXT` varsayılır — geriye uyum):

| Mod | Anlam | `stem`/`options` | `visual` |
|---|---|---|---|
| `STRUCTURED_TEXT` | Soru pypdf metniyle eksiksiz temsil edilir | dolu gövde + tam dört dolu A–D | `null` olmalı |
| `IMAGE_BACKED` | Soru yalnız resmî PDF kırpmasıyla temsil edilir | `null` (boş/eksik metin tutulmaz) | kanıtlı `visual` zorunlu |
| `HYBRID` | Metin + kırpma birlikte taşınır | dolu gövde + tam dört dolu A–D | kanıtlı `visual` zorunlu |

Bilinmeyen bir değer (ör. `AUDIO`) **reddedilir** (`unsupported question representation`);
sessizce yapılandırılmış kola düşmez. `IMAGE_BACKED` kaydı kısmi A–D seti taşıyamaz.

## 2. `question.visual` kanıt bloğu (`$defs/visual`)

| Alan | Kural |
|---|---|
| `authority` | `const "ORIGINAL_MEB_PDF"` — tek kabul edilen kaynak resmî MEB PDF'idir |
| `asset_path` | repo-relative `.png` yol; mutlak yol, `..`, `\`, URL şeması reddedilir |
| `public_path` | site-absolute küçük harf `.png` yol; `..` ve `//` prefix reddedilir |
| `asset_sha256` | kırpma baytlarının küçük harf SHA-256'sı |
| `page` | pozitif tamsayı; onarılan kaydın `question.page_start` değeriyle eşleşir |
| `clip_rect_pt` | `{x0, y0, x1, y1}` sayısal PDF-point sınırları |
| `render_dpi` | ≥ 150 tamsayı (uygulamada 300) |
| `reconstructed_from_ocr` | `const false` — yeniden çizim/OCR yasaktır |

Doğrulayıcılar: `validate_visual()` provenance zincirini denetler;
`validate_structure()` temsil moduna göre kapıyı çalıştırır
(`STRUCTURED_TEXT`/`HYBRID` → dolu gövde + 4 dolu A–D;
`IMAGE_BACKED`/`HYBRID` → kanıtlı `visual` zorunlu).
Görselin kendisi **kanıt sıfırlamaz**: `IMAGE_BACKED` altında eksik option seti
hâlâ reddedilir.

## 3. Kırpma üretimi (kanıt zinciri)

- Kaynak PDF değişmezdir; kırpma yalnız okumayla alınır (PyMuPDF, 300 DPI).
- Bölge bulma: sol marjda `N.` ile başlayan metin blokları soru başlangıcıdır
  (`render_visual_pilot.py: question_anchors` / `region_for`); sonuç `page.rect`
  ile kesiştirilir.
- OCR/MinerU metni `authoritative: false` ile işaretlidir; source-of-truth olmaz.
- R10 onarımı (`repair_structural_gate.py`) **yalnızca** metinle temsil edilemeyen
  kayıtlara uygulanır; temsil edilebilir kayıtlara dokunulmaz. Hiçbir seçenek veya
  cevap üretilmez; `answer: null`, `solution: null` korunur.

## 4. Yayın satırı ve API

- `publish_verified.api_row`: `representation` + `visual{publicPath, page, clipRectPt,
  renderDpi, authority}` taşır; `asset_path`/`asset_sha256` **yayınlanmaz**.
- `app/api/questions/route.ts`: `validVisual()` aynı traversal/authority kurallarını
  uygular. Kapalı enum kontrolü mod dallanmasından **önce** çalışır; bilinmeyen temsil
  yapılandırılmış kola düşemez.
- Cevap anahtarı `toPublicQuestion` ile sunucuda kalır; POST doğrulaması
  `timingSafeEqual` ile yapılır.

## 5. Yaşam döngüsü ve güvenlik sınırları

- Görsel temsil `NEEDS_REVIEW` / `published: false` sınırını kaldırmaz: onarım artefaktı
  (`MEB-LGS-2022__SAYISAL.visual.json`, `visual_backed_record_count: 2`) yayına girmez;
  `publish()` `VERIFIED` olmayan kaydı atlar; `transition(→VERIFIED)` 11 kontrol +
  müfredat kanıtı + çözümü ister.
- Duplicate fingerprint görsel kayıtta görsel kanıtı kullanır, böylece iki gövdesiz
  soru birbirinin kopyası sayılmaz (R11).
- Pilot yüzeyleri (`/pilot-2022`, `/pilot-2022-visual`) `robots: {index: false,
  follow: false}` meta taşır; `public/` altındaki kırpmalar statik inceleme amaçlıdır
  (PD-6 kararı PO'nundur; bu belge yayın politikası icat etmez).
- Kusurlu ham artefakt (`MEB-LGS-2022__SAYISAL.json`, Q15 `D: ""` / Q18 `options: {}`)
  kanıt olarak korunur; onarım ayrı dosyadadır, tarihsel kanıt yeniden yazılmaz.

## 6. Gerçek artefakt kanıtı (2022 Sayısal A)

| Kayıt | Ham durum | Onarım |
|---|---|---|
| `MEB-LGS-2022:SAYISAL:FEN:Q15` | `options.D == ""` → `present but empty: D` | `stem/options: null`, `IMAGE_BACKED`, `img-q15-p28.png` (sayfa 28, 300 DPI) |
| `MEB-LGS-2022:SAYISAL:FEN:Q18` | `options == {}` → `missing A-D keys: A, B, C, D` | `stem/options: null`, `IMAGE_BACKED`, `img-q18-p30.png` (sayfa 30, 300 DPI) |

İki kayıt da `NEEDS_REVIEW`, `confidence: LOW`, `answer: null`; kırpma SHA-256
değerleri `asset_sha256` alanlarında kayıtlıdır ve testlerle gerçek dosya
baytlarıyla doğrulanır.

## 7. Testler

## 8. TASK-QBANK-007 karar kaydı (C3–C5)

- **C3 — görsel asset sınırı:** `mat-q*.png` (TASK-QBANK-003, `pilot.json` + 8 kırpma)
  ile `img-q15/img-q18.png` (TASK-QBANK-005, `.visual.json`) aynı
  `public/pilot-2022-visual/` dizininde durur. Taşıma **yapılmadı**: iki dosya adı
  (`asset_path`/`public_path`) staging artefaktlarına + kırpma SHA-256 değerlerine
  gömülüdür; sessiz taşıma kanıt zincirini kırar. Ayrım dosya-adı önekiyle korunur
  (`mat-` = pilot, `img-` = onarım). PO onayı olmadan dizin bölünmez.
- **C4 — şema sertleştirme:** `canonical_schema.json` → `question.allOf` içinde iki
  `if/then` dalı (`IMAGE_BACKED`/`HYBRID` ⇒ `visual` zorunlu + `$defs/visual`).
  Ters yön eklenmedi (görselin varlığı metin kapısını gevşetmez). Regresyon:
  `test_visual_representation.py::test_schema_declares_representation_and_visual_provenance`.
- **C5 — pilot yayın riski:** sayfa-meta `noindex` korunur; `app/robots.ts` disallow
  listesine `/pilot-2022` + `/pilot-2022-visual` eklendi (savunma derinliği).
  Sitemap pilot rotası içermez, navigasyondan link yoktur. `/calis` yeniden
  tasarlanmadı, yayın politikası icat edilmedi.


- `test_canonical_visual.py` — gerçek artefaktın iki yarısı, temsil değişmezliği,
  kanıt bağı, traversal reddi, `/calis` sızıntı kontrolü.
- `test_visual_representation.py` — R9 sözleşmesi ve R10 gerçek-artefakt kapısı.
- `api-contract.test.mjs` — `IMAGE_BACKED`/`HYBRID` yayın sözleşmesi.
