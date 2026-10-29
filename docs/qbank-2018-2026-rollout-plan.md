# Nüli QBANK 2018–2026 ölçekleme planı

**Durum:** Kapsam kararı alındı  
**Tarih:** 2026-10-07  
**Kapsam:** 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025 ve 2026 resmî LGS soruları

## 1. Kapsam kararı

Nüli'nin soru bankası yalnızca 2022 pilotundan oluşmayacak. Hedef, **2018–2026 arasındaki bütün resmî LGS soru kitapçıklarını ve ilgili resmî cevap anahtarlarını**, kaynak/provenance ve insan doğrulaması kapıları korunarak kanonik QBANK'a almaktır.

2022 Sayısal pilotu nihai kapsam değil, extractor + representation + review workflow için ilk kalite kapısıdır.

## 2. Yıl matrisi

| Yıl | Beklenen kapsam | İlk durum | Sonraki iş |
|---|---|---|---|
| 2018 | Sözel + Sayısal kitapçıklar ve resmî anahtar | Source registry kapsamı ayrıca doğrulanacak | Resmî PDF keşfi ve hash |
| 2019 | Sözel + Sayısal kitapçıklar ve resmî anahtar | Source registry kapsamı ayrıca doğrulanacak | Resmî PDF keşfi ve hash |
| 2020 | Sözel + Sayısal kitapçıklar ve resmî anahtar | Source registry kapsamı ayrıca doğrulanacak | Resmî PDF keşfi ve hash |
| 2021 | Sözel + Sayısal kitapçıklar ve resmî anahtar | Source registry kapsamı ayrıca doğrulanacak | Resmî PDF keşfi ve hash |
| 2022 | Öncelikli Sayısal pilot; diğer kitapçıklar da hedef kapsamda | Repository'de Sayısal pilot mevcut | Pilot gate + kitapçık genişletme |
| 2023 | Sözel + Sayısal kitapçıklar ve resmî anahtar | Registry kaydı mevcut görünüyor | PDF/manifest/extraction doğrulaması |
| 2024 | Sözel + Sayısal kitapçıklar ve resmî anahtar | Registry kaydı mevcut görünüyor | PDF/manifest/extraction doğrulaması |
| 2025 | Sözel + Sayısal kitapçıklar ve resmî anahtar | Registry kaydı mevcut görünüyor | PDF/manifest/extraction doğrulaması |
| 2026 | Sözel + Sayısal kitapçıklar ve resmî anahtar | Registry kaydı mevcut görünüyor | PDF/manifest/extraction doğrulaması |

`2018–2021` için kaynak kaydı veya PDF bulunmuyorsa veri üretilmez. Eksik yıl açık bir source gap olarak tutulur.

## 3. Her kitapçık için yaşam döngüsü

```text
OFFICIAL MEB PDF + ANSWER KEY
  ↓
SOURCE REGISTRY + SHA-256
  ↓
DETERMINISTIC PDF EXTRACTION
  ↓
QUESTION REGIONS + VISUAL ASSETS + MANIFEST
  ↓
SOURCE-FIDELITY QA
  ↓
CANONICAL STAGING
  ↓
AI CANDIDATE ANALYSIS
  ↓
STRUCTURAL / SEMANTIC VALIDATION
  ↓
NEEDS_REVIEW
  ↓
HUMAN ANSWER + CURRICULUM + SOLUTION VERIFICATION
  ↓
VERIFIED
  ↓
PUBLISHED DELIVERY DATA
```

Bir kitapçıkta hata bulunması diğer yıllardaki kayıtların kapılarını gevşetmez. Her kayıt kendi kanıtıyla değerlendirilir.

## 4. İşleme sırası

1. Kaynak registry'yi 2018–2026 tüm yıl/kitapçıklar için tamamla.
2. Her PDF ve resmî cevap anahtarını hash'le; retrieval metadata'yı kaydet.
3. Extractor'ı önce 2022 pilotunda doğrula.
4. AI Studio/Gemini'yi 5–10 temsili soru ile deterministic çıktıya karşı ölç.
5. Pilot düzeltmelerini extractor/canonical dönüşüm katmanına uygula.
6. Kitapçıkları yıl bazında, küçük batch'lerle işle.
7. Her batch için soru sayısı, sayfa, boundary, visual ve warning metriklerini karşılaştır.
8. İnsan review kuyruğunu yıl/kitapçık bazında oluştur.
9. Sadece insan doğrulaması tamamlanan kayıtları `VERIFIED` yap.
10. Tüm corpus doğrulanmadan Supabase ve öğrenci teslimi ölçeklendirmesi yapma.

## 5. Kalite kapıları

Her kayıt için en az:

- source identity, year, booklet;
- PDF SHA-256 ve sayfa/question referansı;
- stem/options/option order fidelity;
- mathematical-symbol fidelity;
- `STRUCTURED_TEXT` / `IMAGE_BACKED` / `HYBRID` kararı;
- visual provenance gerekiyorsa PDF-point crop + DPI + asset hash;
- curriculum candidate ve evidence/status;
- pedagogical difficulty 1–5 + confidence + rationale;
- question type;
- candidate answer ayrı, canonical answer insan doğrulamasına kadar null;
- 11 canonical verification check;
- duplicate kontrolü;
- açık warnings ve unresolved issues.

## 6. Ölçekleme metrikleri

Yıl ve kitapçık bazında raporlanacak:

- PDF sayfa sayısı;
- beklenen ve tespit edilen soru sayısı;
- soru boundary güveni;
- structured/image/hybrid dağılımı;
- eksik/truncated option sayısı;
- symbol/visual warning sayısı;
- duplicate question number sayısı;
- candidate answer sayısı;
- curriculum/difficulty confidence;
- review queue boyutu;
- VERIFIED sayısı;
- publication'a kapalı kayıt sayısı;
- extractor/model karşılaştırma hataları.

## 7. Yetki sınırı

Hermes bu planın teknik uygulamasını, testini ve raporlamasını yapar. Product Owner açıkça karar vermeden:

- canonical answer doldurmaz;
- `VERIFIED` geçişi yapmaz;
- soruları öğrenci teslimine açmaz;
- kaynak boşluğunu tahminle kapatmaz;
- GitHub'a push, merge veya deploy yapmaz.
