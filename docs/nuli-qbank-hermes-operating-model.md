# Nüli QBANK — Hermes çalışma modeli

**Durum:** Aktif proje çalışma sözleşmesi  
**Tarih:** 2026-10-07  
**Kaynak:** `İndirilenler/Nuli_QBANK_Google_AI_Studio_Project_Spec_v1.md` + repository QBANK belgeleri

## 1. Rol değişikliği

Bu proje için Cline kullanılmayacak. Cline'a verilen normal görevleri Hermes Agent yürütecek.

| Rol | Sorumluluk |
|---|---|
| Product Owner | Ürün hedefleri ve materyal kararlar |
| Hermes Agent | Mimari, planlama, uygulama, test, güvenlik, provenance ve handoff |
| Google AI Studio/Gemini | Yalnızca yardımcı analiz; kaynak veya doğrulama otoritesi değil |
| GitHub | Kod ve kanonik içerik kaynak deposu |
| PostgreSQL/Supabase | Kanonik QBANK kararlı hâle geldikten sonraki operasyonel katman |

## 2. Bağlayıcı sınırlar

- Resmî MEB PDF'i tek kaynak otoritesidir.
- AI yalnızca aday üretir: transkripsiyon, görsel sınıflandırma, cevap adayı, müfredat adayı, zorluk ve soru tipi.
- `answer_key.answer` insan doğrulaması olmadan doldurulmaz.
- AI hiçbir kaydı `VERIFIED` yapamaz.
- Belirsizlikte tahmin yapılmaz; `NEEDS_REVIEW` ve açık uyarı yazılır.
- `STRUCTURED_TEXT`, `IMAGE_BACKED` ve `HYBRID` ayrımı korunur.
- PDF SHA-256, PDF sayfası, PDF-point crop, DPI, asset hash ve uyarılar korunur.
- Öğrenci PII'si soru bankası ve ingestion çıktısına girmez.
- Hedef corpus kapsamı **2018–2026 arasındaki bütün resmî LGS sorularıdır**. 2022 Sayısal pilotu yöntem doğrulama kapısıdır; nihai kapsam sınırı değildir.
- Her yıl/oturum/kitapçık ayrı source registry kaydı, PDF hash'i, extraction manifest'i ve review kuyruğuyla işlenir.
- Bir yılın kaynağı bulunamadığında kayıt uydurulmaz; yıl `SOURCE_GAP`/`NEEDS_REVIEW` olarak raporlanır ve yayınlanmaz.
- Kanonik soru bankası kararlı olmadan Supabase migrasyonu yapılmaz.
- `/calis` staging veya AI çıktısını doğrudan tüketmez; yalnızca doğrulanmış delivery kayıtlarını tüketir.

## 3. Hermes görev akışı

1. Repository durumunu, branch'i ve mevcut diff'i incele.
2. `AGENTS.md` ve QBANK dokümanlarını oku.
3. Görevi kaynak, extraction, schema, content, visual, curriculum, answer veya publication katmanına sınıflandır.
4. Küçük ve geri alınabilir bir değişiklik planla.
5. Resmî kaynağı ve SHA-256 provenance'ı koruyarak uygula.
6. Herhangi bir AI/model çıktısını aday olarak işaretle.
7. İlgili Python/Node testlerini ve `npm run build` kontrolünü çalıştır.
8. Diff, secret/PII, answer-key sızıntısı ve status geçişlerini denetle.
9. Handoff belgesi yaz; kalan insan kararlarını açıkça belirt.
10. Product Owner onayı olmadan `VERIFIED`, yayınlama, merge, push veya deploy yapma.

## 4. AI Studio pilotunun konumu

AI Studio pilotu deterministik extractor'ın yerine geçmez. Önce 5–10 temsili soru üzerinde ölçülür:

- metin ve seçenek sadakati;
- matematik sembolü sadakati;
- görsel gereksinimi;
- soru sınırı;
- cevap adayı doğruluğu;
- müfredat adayı;
- 1–5 pedagojik zorluk ve güven;
- JSON uyumu;
- belirsizlik/halüsinasyon;
- süre, maliyet ve tekrarlanabilirlik.

Pilot sonucu yalnızca `REPLACE`, `SUPPLEMENT` veya `SECONDARY` önerisi verebilir; otomatik yayın kararı veremez.

## 5. Agent/MCP kararı

Yürütücü Hermes'tir. Hermes gerektiğinde ayrı inceleme işlerini `delegate_task` ile şu çalışma akışlarına bölebilir: mimari, soru/provenance, eğitim/pedagoji, güvenlik/KVKK ve test.

Bu iş için yeni MCP sunucusu eklenmedi. Mevcut dosya, terminal, web, tarayıcı ve hesaplama araçları PDF ingestion ve review kuyruğu için yeterlidir. Yeni bir MCP ancak mevcut araçların karşılayamadığı somut bir dış sistem entegrasyonu gerektiğinde ve Product Owner onayıyla eklenir.

## 6. KerimHoca curated corpus policy

Product Owner kararıyla KerimHoca'nın `LGS Çıkmış Sorular 2018–2026` sayfası, resmî sınav PDF'lerini yıl/oturum/ders bazında gruplandıran **güvenilir küratörlü dağıtım kaynağı** olarak kabul edilir. Bu sayfadaki bağlantıları extraction için doğrudan kullanacağız; her soruyu ayrıca MEB sayfasından tekrar indirmek zorunlu değildir.

Yine de her indirme için kaynak zinciri korunur: KerimHoca sayfası, Drive/file URL veya ID, PDF SHA-256, dosya metadata'sı, yıl, bölüm, ders, sayfa ve soru numarası. Kırpma ve extraction doğrudan bu dosyalardan yapılabilir.

Bu karar rutin kaynak tekrarı ihtiyacını kaldırır; fakat canonical answer, curriculum mapping, duplicate kontrolü, visual representation, structural validation ve insan review kapılarını kaldırmaz. KerimHoca bağlantısında açıkça bulunmayan bir bilgi uydurulmaz.


## 7. Kabul ölçütü

Trustworthy QBANK lifecycle:

```text
OFFICIAL SOURCE
→ SOURCE REGISTRY + SHA-256
→ DETERMINISTIC EXTRACTION
→ SOURCE-FIDELITY QA
→ CANONICAL STAGING
→ AI CANDIDATE ANALYSIS
→ AUTO VALIDATION
→ NEEDS_REVIEW
→ HUMAN VERIFICATION
→ VERIFIED
→ DELIVERY API
```

Hiçbir sonraki katman önceki başarısız katmanı atlayamaz.
