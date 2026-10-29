# NÜLİ QUESTION INGESTION SPEC v1

**Görev:** TASK-QBANK-004 · **Tarih:** 2026-10-04 · **Kapsam:** Analiz ve spesifikasyon (kod değişikliği yok)
**Durum:** Mevcut sistem kod, veri ve testlerle uçtan uca doğrulandı. Aşağıdaki her "VERIFIED" ifadesi
çalıştırılmış bir kontrole dayanır; "OBSERVED" ifadesi kaynak kod okumasıdır.
**Tamamlanma notu:** İlk koşu sağlayıcı hatasıyla kesildi; §15–§17 ve doğrulama eki **devam koşusunda**
(yeniden canlı kontrol + twin-check ile) tamamlandı. Bu koşuda iki **yeni** bulgu eklendi: `R9`
(görsel temsilin canonical karşılığı yok) ve `R10` (gerçek 2022 staging dosyası yapısal kapıdan geçmiyor).
Belge **§0–§17 + doğrulama eki** olarak tamdır. Kod, commit, push, merge ve deploy **yapılmadı**.

**TASK-QBANK-005 uygulama notu (2026-10-05):** `R9` ve `R10` kod düzeyinde ele alındı.
Şema `question.representation` + kanıtlı `question.visual` alanlarını; validator temsil
moduna göre yapısal kapıyı çalıştırır. **R10 iki artefaktla okunmalıdır:**
`scripts/source-ingestion/data/questions/staging/MEB-LGS-2022__SAYISAL.json`
(ham pypdf çıktısı, kanıt amaçlı korunur) içinde `FEN:Q15` (`D: ""`) ve `FEN:Q18`
(`options: {}`) **bilinçli olarak açık validation failure olarak kalır**
(her ikisi `NEEDS_REVIEW`, `confidence: LOW`, `answer: null`, seçenek/cevap uydurulmaz);
`scripts/source-ingestion/data/questions/staging/MEB-LGS-2022__SAYISAL.visual.json`
ise aynı iki kaydın resmî PDF kırpmasıyla (`IMAGE_BACKED`, `NEEDS_REVIEW`,
`published: false`) temsil edilebildiğini gösteren **ayrı onarım artefaktıdır** —
üretim yayını/`VERIFIED` değildir. Ayrıntı ve kanıt için
`docs/question-visual-representation-v1.md`.

**Okuma kuralı:** Bu belge gerçek durumu anlatır. "Şu anda yok" denilen her şey bu belgede
"yok (2026-10-04 itibarıyla)" olarak işaretlidir; bu bir eksiklik listesi değil, ölçülmüş durumdur.

---

## 0. Yönetici özeti

MEB LGS PDF'inden güvenilir soru üretme boru hattı **2022 Sayısal A kitapçığında uçtan uca çalışıyor**
ve tasarım gereği hiçbir aşamada kendiliğinden `VERIFIED` oluşturmuyor. Provenance zinciri
(SHA-256 + redirect + host allowlist + karantina), aday çıkarımı, cevap anahtarı eşleştirmesi,
görsel kırpma ve 11 kontrollü yayın kapısı kodda ve testlerde karşılığını buluyor.

Bununla birlikte analiz, 2018–2026 hedefine giderken engel olacak **yedi gerçek risk** ortaya koydu.
En kritik ikisi şunlar:

1. **Ders başlığı kapsamı dar** (`F-1`): `SUBJECT_HEADERS` sözlüğünde
   `DİN KÜLTÜRÜ VE AHLAK BİLGİSİ` yok. Bu başlık altındaki sorular **yanlış derse atanıyor**
   (sessiz kayıp değil, sessiz *yanlış etiketleme* — daha tehlikeli). Kanıt: §5.3.
2. **Kitapçık kimliği kayıtta yok** (`F-2`): staging kayıtları `booklet: "SAYISAL"` diyor,
   oysa indirilen PDF `“A” KİTAPÇIĞI` ve 2025/2026'da A/B/C/D ayrı kitapçıklar var.
   Aynı yılın B kitapçığı aynı `--booklet SAYISAL` ile işlenirse **aynı `id`'ler** üretilir ve
   cevap anahtarı sessizce **yanlış kitapçığın**ki olur. Kanıt: §6.4.

Bu iki bulgu, spec'in hedef mimarisinde "kitapçık kimliği"ni birincil kimlik parçası yapan
tasarımı zorunlu kılmaktadır.

---

## 1. Current System Architecture

Pipeline tamamen `scripts/source-ingestion/` altında, Python stdlib + `pypdf` ile yaşamaktadır.
UI, `/api/questions`, soru deposu ve AI rotaları bu boru hattından **bağımsızdır** (OBSERVED).

| # | Aşama | Araç | Girdi → Çıktı | Durum |
|---|---|---|---|---|
| 1 | Kayıt defteri | `validate_source_registry.py` | `data/source-engine/config/source-registry.json` → doğrulama | 6 resmî kayıt, VERIFIED (çalıştırıldı) |
| 2 | Keşif + indirme | `download_official_pdfs.py` | registry sayfası → `archive/*.pdf` | Çalışıyor; run başına 1–3 PDF sınırı |
| 3 | Manifest | `create_ingestion_manifest.py` | yerel PDF → `manifests/*.json` | Çalışıyor; SHA-256 zorunlu |
| 4 | Aday çıkarımı | `extract_pdf_candidates.py` | PDF + manifest → `staging/*.json` | Çalışıyor; **hep** `NEEDS_REVIEW` |
| 5 | İnceleme kuyruğu | `build_review_queue.py` | staging → `review-queue*.json` | Çalışıyor; tüm kontroller `false` |
| 6 | Yapısal doğrulama | `validate_canonical.py` | staging → hata listesi | Çalışıyor; durum değiştirmez |
| 7 | Görsel kırpma | `render_visual_pilot.py` | PDF + `targets.json` → PNG + `pilot.json` | Pilot düzeyinde (bkz. §7) |
| 8 | Yayın | `publish_verified.py` | staging → `questions.json` | **0 kayıt** üretir (aşağıda) |
| 9 | API | `app/api/questions/route.ts` | `data/questions/questions.json` → JSON | **Boş depo → `{items:[],count:0}`** |
| 10 | UI | `app/calis` → `components/study-flow.tsx` | `data/content.ts` `questionBank` | **Boru hattından bağımsız demo banka** |

**Katman ayrımı (task'ın kritik ilkesi) — mevcut kodda karşılığı:**

| Katman | Nerede | Authoritative? |
|---|---|---|
| MEB SOURCE | `archive/*.pdf` + `manifests/*.json` | ✅ Tek source-of-truth |
| STRUCTURED QUESTION CONTENT | `staging[].question.{stem,options}` | ⚠️ pypdf türevi, doğrulanmamış |
| VISUAL CONTENT | `pilot-2022-visual/*.png` | ✅ Resmî sayfa rasterı (yeniden kurulum yok) |
| OFFICIAL ANSWER KEY | `staging[].extraction.answer_key_map` | ⚠️ Aday (candidate) — `answer_key.answer` **hep `null`** |
| NÜLİ SOLUTION | `staging[].solution` | ❌ **Her kayıtta `null`** |
| NÜLİ PEDAGOGICAL ANALYSIS | `curriculum.*` | ❌ Her iki katman da `UNMAPPED` |

Doğrulama (çalıştırıldı): 34 kaydın **34'ünde** `answer_key.answer === null`,
iki curriculum katmanı da `UNMAPPED`, `solution` `null`. Yani üst üç satır (answer/solution/pedagoji)
**zaten ayrıştırılmış ve boş** durumdadır — bu, task'ın istediği ayrımın kod tarafında fiilen
var olduğunun kanıtıdır. Ayrımın *zayıf* olduğu tek yer: `answer_key.candidate` ile
`answer_key.answer` aynı nesnede adlandırılıyor ve test kapsamı ikisini ayırmıyor (§12, `F-7`).

---

## 2. Current PDF → Question Data Flow

Gerçek zincir (2022 Sayısal A üzerinde izlendi, `sha256=8a1c6526…c4142`):

```
MEB sayfası (odsgm.meb.gov.tr …/icerik/822)
  │  download_official_pdfs.resolve_pdfs   — yalnız registry'deki tam HTTPS URL
  │  SafeRedirect(kind="official_page")    — her hop MEB allowlist'te kalmalı
  ▼
HTML'den PDF linkleri (anchor metniyle kitapçık seçimi)
  │  DiscoveredPdf(source_id, anchor_text, discovery_redirect_chain)
  │  validate_discovered_pdf                — kanıtsız PDF reddedilir
  ▼
cdn.eba.gov.tr PDF indirme (allowlist'te tek istisna)
  │  download_pdf → geçici dosya → .pdf imzası + Content-Type + boyut(≤100MiB) kontrolü
  │  hedef zaten varsa: hash farklıysa HATA (değişen byte sessizce ezilmez) ✅ idempotent
  ▼
data/questions/archive/MEB-LGS-2022/01-2022_….pdf   (immutable, 7.976.321 B)
  │  create_manifest → streaming SHA-256 + provenance doğrulaması
  ▼
manifests/MEB-LGS-2022__8a1c6526b50b.json
    status=NEEDS_REVIEW, published=false, provenance_status=DISCOVERED,
    usage_rights_review=UNREVIEWED, resulting_record_count=0
  │  extract_pdf_candidates.extract
  │  ├─ validate_manifest_for_pdf — id/hash/status/size/Content-Type/index-URL eşleşmeli
  │  ├─ extract_text (pypdf, sayfa hata izole edilir)
  │  ├─ parse_answer_key          → by_subject[subject][qno] = {letter,page,evidence}
  │  ├─ segment_lines            → soru blokları + ORPHAN_NUMBER raporu
  │  └─ kayıt üretimi             → answer=her zaman null, 11 kontrol hep false
  ▼
staging/MEB-LGS-2022__SAYISAL.json   (34 aday, 33 sayfa)
  │  build_review_queue → fingerprint + 11 kontrol false
  ▼
review queue (PO incelemesi)  ──[insan: 11 kontrolü tek tek true yapar]──▶
  │  validate_canonical.transition(→VERIFIED)  ← 11 kontrolün tamamı true olmadan reddeder
  ▼
publish_verified.api_row → data/questions/questions.json
  │  app/api/questions (yalnız VERIFIED + tüm kontroller true olan satırları okur)
  ▼
GET /api/questions (answer/verification/sourceHash yanıttan çıkarılır)  ← HİÇBİR UI ÇAĞRISI YOK
```

**2022 pilotu sayısal özeti** (doğrudan `staging/MEB-LGS-2022__SAYISAL.json`'den okundu):

| Ölçüt | Değer |
|---|---|
| PDF sayfası | 33 (sayfa 33 = cevap anahtarı) |
| Üretilen aday | **34** (FEN BİLİMLERİ 20 + MATEMATİK 14) |
| Cevap anahtarı çifti (reg-ex ile bulunan) | 44 |
| Konuya eşlenmiş anahtar | MATEMATİK 20, FEN BİLİMLERİ 20 → `mapped_candidates=34`, `unmapped=0`, `subject_conflicts=0` |
| Metin bloğu üretilemeyen sorular | **6**: MAT Q4(p3), Q10(p7), Q11(p8), Q12(p9), Q14(p11), Q19(p15) |
| Uyarılı kayıt | 2 (FEN Q16, FEN Q18) |
| `review_reasons` | `question_or_option_extraction_ambiguous`, `question_numbers_without_text_block` |
| `VERIFIED` / yayınlanan | **0 / 0** |

**Twin-check (bağımsız yeniden hesaplama):** PDF yeniden okunup `parse_answer_key` ve
`segment_lines` yeniden çalıştırıldı; staging'deki **34 adayın 34'ünde** harf eşleşmesi birebir
aynı (`mismatch=[]`), 33 sayfanın hiçbiri boş metinli veya hatalı değil. Yani staging çıktısı
deterministik olarak yeniden üretilebilir — bu, spec'in "deterministik çıkarım" varsayımını doğrular.

---

## 3. Current Schema / Data Model

### 3.1 Canonical kayıt — `scripts/source-ingestion/canonical_schema.json` (JSON Schema, `schema_version: "1.0"`)

```
record (required: schema_version,id,source,question,answer_key,curriculum,extraction,solution,status,checks)
├─ id            "MEB-LGS-2022:SAYISAL:MATEMATİK:Q01"
├─ source        source_id, source_type{REAL_LGS|MEB_SAMPLE}, year≥2018,
│                official_index_url, source_page_url, discovered_from, pdf_url, final_url,
│                source_file_url, redirect_chain[≥1], source_sha256[64-hex], booklet, question_number
├─ question      grade=8, subject, stem, options{A..D}, page_start, page_end
├─ answer_key    candidate{A-D|null}, answer{A-D|null}, authority="OFFICIAL_MEB_ONLY",
│                source_verified, answer_key_verified          ← ikisi de extraction'da false
├─ curriculum    LGS_REFERENCE_2018_PLUS + CURRENT_TYMM  (her biri status/version/subject/unit/
│                topic/learning_outcome/skill/evidence_url)   ← ikisi de UNMAPPED
├─ extraction    method, retrieved_at, confidence{LOW|UNREVIEWED|HUMAN_REVIEWED},
│                warnings[], answer_key_candidates[], answer_key_map
├─ solution      string|null                                   ← hep null
├─ status        DRAFT|EXTRACTED|AUTO_CHECKED|NEEDS_REVIEW|VERIFIED|REJECTED
└─ checks        11 boolean kontrol                             ← hep false
```

### 3.2 Diğer katmanlar

| Artefakt | Şema/şekil | Üretici | Tüketici |
|---|---|---|---|
| Registry kaydı | `{id,type,year,official_index_url,booklets[]}` | insan | tüm scriptler |
| Manifest | provenance + `sha256/size_bytes/retrieved_at/parser_version/resulting_record_*` | `create_ingestion_manifest.py` | `extract_pdf_candidates.py` |
| Staging dosyası | `{schema_version,source_id,source_sha256,pages[],records[],answer_key_summary,unparsed_question_numbers,review_reasons,status,published}` | `extract_pdf_candidates.py` | review queue, validate, publish |
| Review queue | `{count, items[{record_id,source_id,question_number,page_start,page_end,status,candidate_fingerprint,possible_duplicate_indices,checks}]}` | `build_review_queue.py` | PO |
| API satırı | `{id,sourceId,sourceType,year,booklet,subject,grade,questionNumber,stem,options,answer,solution,status,curriculum{layer,…},verification,sourceHash}` | `publish_verified.api_row` | `/api/questions` |
| DB şeması | `db/001_question_bank.sql` — **uygulanmamış**, gözden geçirme amaçlı | — | — |

**Kimlik:** `id` = `{source_id}:{booklet}:{subject_label}:Q{nn}`. `subject_label`
`(subject or "BILINMIYEN").split()[0]` ile kısaltılır → `MATEMATİK`, `FEN`.
Bu, `canonical_schema.json`'ın `additionalProperties:false` ile zorladığı tek makine-okunur kayıttır.

### 3.3 /api/questions satır şeması ile canonical arasındaki fark

`publish_verified.api_row` iki curriculum katmanından **`status=="VERIFIED"` olan ilkini** seçer
ve **tek** katmanı API'ye yazar. Yani iki katman canonical'da korunur, yayın anında **birebir
indirgenir**. Kayıp: `evidence_url` yayın satırına taşınmaz (satırda `version` var, `evidence_url` yok).
Bu, provenance zincirinin yayın noktasında kısmen kesildiği tek yerdir (§15, `S-4`).

---

## 4. Source & Provenance Contract

**Mevcut sözleşme (koda bağlı, hepsi testli):**

1. **Host allowlist.** Sayfa/keşif hostları: `official_host()` = `meb.gov.tr` / `meb.k12.tr`
   (alt alan adları dahil). PDF hedefi ayrıca `cdn.eba.gov.tr` olabilir (`source_trust.CDN_HOST`).
   `canonical_schema.json` bunları URL regex'iyle de zorlar.
2. **Keşif kanıtı zorunlu.** `DiscoveredPdf` içermeyen bir PDF reddedilir
   ("PDF target requires official-page discovery evidence").
3. **Redirect zinciri.** `SafeRedirect` her hopu doğrular ve zinciri kaydeder; zincirin ilk elemanı
   `pdf_url`, son elemanı `final_url` olmak zorundadır (`validate_provenance`).
4. **Bütünlük.** Manifest SHA-256'sı arşivlenmiş PDF'in SHA-256'sıyla **eşleşmek zorunda**;
   `validate_manifest_for_pdf` ayrıca `source_id`, `size_bytes`, `content_type`, `official_index_url`
   ve `source_file_url == pdf_url` eşleşmesini de doğrular. Uyuşmazlıkta `parser.error` → **çıkış**.
5. **İdempotency.** Dosya zaten varsa hash karşılaştırılır; farklıysa hata. Aynı PDF tekrar
   indirilmez, üstüne yazılmaz.
6. **Karantina.** Geçersiz artifact'ler (`24220837_alte_fullmembershipcertificate.pdf`,
   `sha=cf9b2e30…`) altı ayrı manifest'te `status=REJECTED`, `published=false`, `rejection_reason`
   dolu olarak durur ve `test_manifest_quarantine.py` bunları sayı olarak sabitler (**6**).
7. **Politika sınırı.** `REAL_LGS` ve `year≥2018` zorunlu; TEOG/pre-2018 reddedilir.

**2022'de ölçülen değer:** `sha256=8a1c6526b50b4b695dd6f48bfce42c7fbed53d26f0057e554f666cb4682c4142`,
7.976.321 B, `content_type=application/pdf`, tek hoplu redirect zinciri, `parser_version=source-ingestion-pipeline-v1`.

> **Bulgu (P-1, düşük önem):** Beş yılın (2023–2026) arşivi yalnızca karantina sertifikasından oluşuyor.
> Yani **yalnız 2022 gerçek kitapçık PDF'sine sahibiz.** 2018–2026 hedefi için 2018–2021
> yılları registry'de **hiç yok** (`MEB-SAMPLE-ARCHIVE` dönem listesi var ama `REAL_LGS` kaydı yok) —
> 2018–2021 için içe aktarma bugün **yapılamaz**, çünkü kayıt defteri o kaynakları içermiyor.

---

## 5. Text Extraction Contract

### 5.1 Sınırlar nasıl belirleniyor?

`extract_pdf_candidates.segment_lines` (sayfa 117–172) dört kuralı uygular:

| Kural | Davranış | Gerekçe (kod yorumu) |
|---|---|---|
| `QUESTION_START = ^\s{0,4}(\d{1,2})\.\s+(\S.*)$` | satır başında 1–2 haneli numara + boşluk + içerik | kitapçıkta soru numarası satır başında |
| Ders başlığı kapısı | `SUBJECT_HEADERS`'da bir başlık görülene kadar satırlar yok sayılır | sınav talimatı/kapak soru değildir |
| Yetersiz seçenek işareti | `option_marker_count(body) < 1` ise blok soru **değildir** | cevap anahtarı satırları ve alt maddeler elenir |
| Alt madde | `number < current_number` ise ana sorunun gövdesine eklenir | numaralandırma ana→alt yönünde değil |
| Kapanış | 4 seçenek tamamlanınca sonraki satırlar bu soruya eklenmez | kapak/cevap anahtarı metni bulaşmasın |

Seçenek ayrıştırma `parse_options`: yalnız **A→B→C→D sırasına tam uyan** işaretler kabul edilir;
eksik/karışık dizilerde **uydurma seçenek üretilmez** (`{}` döner). Bu, sessiz bozulma yerine
sessiz *eksiklik* tercih ettiğimiz yerdir ve doğru davranıştır.

### 5.2 Sessiz kayıp nasıl raporlanıyor?

`ORPHAN_NUMBER = ^\s{0,4}(\d{1,2})\.\s*$` deseni, gövdesi satır başında tek başına kalan
(şekil/tablo/grafik içeren) soruları yakalar. Bu numaralar `parsed_numbers` içinde yoksa
`unparsed_question_numbers` listesine girer ve `review_reasons`'a `question_numbers_without_text_block`
eklenir. Yani **6 sorunun kaybı sessiz değil, kayıtlıdır** — doğrulandı (§2).

### 5.3 ⚠️ `F-1` — Ders başlığı kapsamı yetersiz (KRİTİK, kanıtlı)

`SUBJECT_HEADERS` şu 5 anahtardır: `DİN KÜLTÜRÜ`, `FEN BİLİMLERİ`, `MATEMATİK`,
`SOSYAL BİLGİLER`, `TÜRKÇE`.

**MEB'in gerçek başlığı `DİN KÜLTÜRÜ VE AHLAK BİLGİSİ`'dir** ve bu listede **yoktur.**
Bu bir 2022 Sayısal (sözel-olmayan) kitapçıkta görünmez; **her sözel kitapçıkta görünür.**

Bağımsız yeniden çalıştırma (`segment_lines`, gerçek `extract()` akışıyla birebir aynı stream
şekli: başlık kendi satırı olarak):

```
BLOCKS=3
  subject='TÜRKÇE'              qno=1  stem='Bu bir Türkçe sorusudur…'
  subject='SOSYAL BİLGİLER'     qno=1  stem='Bu bir sosyal bilgiler sorusudur…'
  subject='SOSYAL BİLGİLER'     qno=1  stem='Bu bir din kültürü sorusudur…'   ← YANLIŞ ETİKET
```

**Etkisi (üç katmanlı, hepsi gerçek):**

1. **Yanlış `subject`** → kayıt `SOSYAL BİLGİLER` kimliğiyle üretilir.
2. **Yanlış cevap anahtarı eşleşmesi** → Din Kültürü Q1'in harfi, *Sosyal Bilgiler* Q1'in
   harfiyle eşleştirilir. `parse_answer_key` de aynı sözlüğü kullandığı için iki blok da
   `SOSYAL BİLGİLER` altında birleşir → **çakışma**. `extract` bunu `subject_conflicts`
   olarak saymaya hazırlıklıdır ama bu senaryoda sessizce birleşir.
3. **Sessiz kayıp değil, sessiz bozulma** — `ORPHAN_NUMBER` bunu yakalamaz, çünkü soru numarası
   satırda metinle birlikte gelmiştir. `review_reasons` temiz kalabilir.

2022 Sayısal'de bu görünmediği için mevcut testler geçiyor; **sözel kitapçık hiç işlenmediği için
test paketi bu boşluğu yakalayamıyor.**

**Düzeltme yönü (karar PO'ya bırakıldı, kod değiştirilmedi):** `SUBJECT_HEADERS`'ı tam başlık
eşlemesine geçirmek (`DİN KÜLTÜRÜ VE AHLAK BİLGİSİ` → `DİN KÜLTÜRÜ`) *ve* başlık listesi
taşmadığında `NO_SUBJECT_HEADER` gibi bir `review_reason` üretmek. §16, `T-1`.

### 5.4 Uyarı sözlüğü (mevcut, kanıtlı)

| Uyarı | Anlamı | 2022'de |
|---|---|---|
| `short_or_incomplete_stem` | gövde < 20 karakter | 0 |
| `four_options_not_confidently_extracted` | 4 seçenek tam gelmedi | **1** (FEN Q18) |
| `option_boundary_ambiguous` | seçenek metninde başka işaret var | **1** (FEN Q16) |
| `low_text_density_or_scanned_content` | gövde < 45 karakter | 0 |

`confidence` uyarısız kayıtta `UNREVIEWED`, uyarılı kayıtta `LOW` olur (34 kayıtta: 32 + 2).

**Örnek (FEN Q16, gerçek çıktı):** `B: "Bor (B) elementi ve karbon ("`, `C: "elementi- nin … C) Lityum…"`
→ seçenek sınırları **kaymış**. Kayıt yine de üretildi, yalnızca uyarıyla işaretlendi.
Bu, "metin-çıkarılabilen ama sınırı bozuk" ara durumu doğru tanımlar; ancak **`validate_canonical`
uyarıya bakmıyor** (§10).

---

## 6. Answer Key Contract

### 6.1 Eşleştirme nasıl yapılıyor?

`parse_answer_key(pages)` (sayfa 200–305) bilinçli olarak muhafazakârdır:

1. **Sayfa seçimi:** satırlarından birinde `CEVAP ANAHTAR` geçmeli (2022'de yalnız **sayfa 33**).
2. **Blok kurgusu:** `ANSWER_LINE = ^\s{0,4}(\d{1,2})\s*[).:-]\s*([A-D])\s*$` ile ardışık çiftler
   bir blok oluşturur.
3. **Konu etiketi — kritik detay:** MEB kitapçık düzeninde ders etiketi cevap bloğunun **altında**
   yer alır (satır etiketi). Kod hem `leading_label` (önceki etiket) hem `trailing_label` (sonraki
   etiket) toplar ve ikisi çakışırsa (`len(labels) > 1`) bloğu **reddeder**.
4. **Reddetme kuralları (sessiz eşleme yok):**
   - ders kanıtı yoksa → eşlenmez (`"{n} answer pairs have no subject evidence; not mapped"`)
   - tanınmayan etiket (`EDEBİYAT` gibi) → blok reddedilir
   - aynı numara iki kez geçerse (`duplicates`) → blok reddedilir
   - çifti olmayan blok → yok sayılır ve `diagnostics`'e yazılır
5. **Çıktı:** `by_subject[subject][question_number] = {letter, page, evidence}`.

**Bağımsız doğrulama (twin-check, yeniden çalıştırıldı):**
```
subjects {'MATEMATİK': 20, 'FEN BİLİMLERİ': 20}   diagnostics []
MAT20 {'letter':'B','page':33,'evidence':'“A” KİTAPÇIĞI CEVAP ANAHTARI (page 33, subject MATEMATİK)'}
FEN20 {'letter':'D','page':33,'evidence':'“A” KİTAPÇIĞI CEVAP ANAHTARI (page 33, subject FEN BİLİMLERİ)'}
staging ile karşılaştırma → mismatch []
```
MAT Q20 = **B**, FEN Q20 = **D** — aynı soru numarasının iki derste bağımsız eşlendiği
`test_answer_key_mapping.py` içinde de sabitlenmiştir. Doğru davranış.

### 6.2 MEB cevap anahtarı ile Nüli çözümü ayrıştırılmış mı?

**Evet, kod düzeyinde ayrıştırılmış ve fiilen boş.** Doğrulanan durum:

| Alan | Kaynak | Değer (34/34 kayıt) |
|---|---|---|
| `answer_key.candidate` | MEB PDF metni | harf (örn. `D`) |
| `answer_key.answer` | **yalnız insan doğrulaması** | **`null`** |
| `answer_key.source_verified` / `answer_key_verified` | insan | **`false` / `false`** |
| `solution` | Nüli | **`null`** |

`test_answer_key_mapping.py::test_mapping_never_writes_the_answer_field` bunu her kayıt için
ayrı ayrı doğruluyor. Yani **bir araç, LLM, OCR veya regex hiçbir koşulda canonical `answer`
yazamaz** — bu, task'ın "OCR/LLM source-of-truth olmamalı" ilkesinin bugün fiilen uygulandığının kanıtıdır.

### 6.3 `answer_key_candidates` ile `answer_key_map` farkı

`answer_key_candidates` = o konudaki **tüm** çiftlerin dökümü (20 kayıt);
`answer_key_map` = yalnız **eşleşen** kaydın kanıtı (`letter`, `page`, `evidence`, `source_sha256`).
`mapped_candidates=34`, `unmapped=0` → 34 adayın 34'ü eşleşti. Eşleşmeyenler olsaydı
`answer_key_mapping_incomplete` `review_reason`'ı üretilirdi.

### 6.4 ⚠️ `F-2` — Kitapçık kimliği kayıtta doğrulanmıyor (KRİTİK, kanıtlı)

**Gözlenen durum:**
- Kaydedilen `source.booklet` = **`"SAYISAL"`** (komut satırından gelen serbest metin).
- PDF'in kendi metni = **`“A” KİTAPÇIĞI` CEVAP ANAHTARI** (sayfa 33, doğrulandı).
- Registry: 2022/2023/2024 → `["SAYISAL","SOZEL"]`; **2025/2026 → `["SAYISAL_A"…"SAYISAL_D"]`**.
- `id` = `MEB-LGS-2022:SAYISAL:MATEMATİK:Q01` → **kitapçık harfi kimlikte yok.**
- Kodun hiçbir yeri PDF'teki `“A” KİTAPÇIĞI` ifadesini `source.booklet` ile karşılaştırmıyor.

**Somut risk (2025/2026 için):** `--booklet SAYISAL` ile hem A hem B kitapçık işlenirse
`{source_id}:SAYISAL:{subject}:Q01` kimlikleri **çakışır** ve her iki kitapçığın cevap anahtarı
tek havuzda birleşir. `extract` bu durumda `subject_conflicts` sayacını artırmaz çünkü çakışma
kitapçık boyutunda, konu boyutunda değildir. Sonuç: **yanlış kitapçığın cevabı doğru görünür.**

**Ayrıca:** `validate_canonical` yalnız `str(source.get("booklet","")).strip()` boş mu diye bakar —
`"SAYISAL"` ve `"SAYISAL_C"` arasındaki farkı göremez. `booklet_verified` kontrolü **insan
onayına** bırakılmış tek kanıttır; otomatik doğrulama yoktur.

**Düzeltme yönü (karar PO'ya bırakıldı):** PDF'in kendi kitapçık başlığını okuyup
`source.booklet`'in türetilmiş karşılığını `source.booklet_evidence` olarak kaydetmek ve
uyumsuzlukta `booklet_mismatch` `review_reason`'ı üretmek. §15 `S-1`, §16 `T-2`.

---

## 7. Visual Question Contract

### 7.1 Orijinal PDF görseli source-of-truth olarak korunuyor mu?

**Evet, ve bu pilotun en güçlü tarafı.** `render_visual_pilot.py`:

- Kaynak PDF **değişmez**; kırpma yalnızca okuma ile yapılır.
- Metin **OCR ile yeniden kurulmaz**: `reconstructed_from_ocr: false`, `method: "page_render_clip"`.
- PNG, resmî sayfanın **birebir 300 DPI raster gösterimidir** (`RENDER_DPI=300`).
- Çıktı `NEEDS_REVIEW` / `published=false`.
- **Cevap anahtarı bilinçli olarak çıktıya yazılmaz** (kod yorumu satır 190).

### 7.2 Crop/bbox nasıl hesaplanıyor?

`question_anchors(page)`: PyMuPDF metin bloklarında `x0 ≤ START_COLUMN_MAX_X (80.0)` olan ve
`^\s*(\d{1,2})\.\s` ile başlayan bloklar → `(y0, numara)`.
`region_for(page, qno)`: başlangıç `y0`; bitiş = sonraki ankastanın üstü, yoksa
`CONTENT_BOTTOM_Y (735.0)`; `PAD_PT=6.0` ile genişletilir; sol/sağ kenar = bölgeye düşen blokların
min/max `x0`/`x2`. Sonuç `page.rect` ile kesişştirilir.

### 7.3 Crop doğrulaması (bağımsız twin-check, yeniden hesaplandı)

Sekiz kaydın tamamı için `region_for` yeniden çağrılıp saklanan `clip_rect_pt` ile karşılaştırıldı
ve 300 DPI pixmap yeniden üretilip `pixel_width/height` ile karşılaştırıldı:

```
Q04 p3  rect_match=True dims_match=True in_page=True
Q10 p7  rect_match=True dims_match=True in_page=True
Q11 p8  rect_match=True dims_match=True in_page=True
Q12 p9  rect_match=True dims_match=True in_page=True
Q14 p11 rect_match=True dims_match=True in_page=True
Q19 p15 rect_match=True dims_match=True in_page=True
Q06 p4  rect_match=True dims_match=True in_page=True
Q13 p10 rect_match=True dims_match=True in_page=True
verified 8 / 8
```

Yani **kırpma geometrisi deterministik ve yeniden üretilebilir.** 8 PNG, `public/pilot-2022-visual/`
altında, toplam ~1.2 MB.

### 7.4 Görsel soruların mevcut temsili

`pilot-2022-visual/pilot.json`: 8 kayıt — **6 `mode:"image"`** (`IMAGE_BACKED`, `structured_text: null`)
+ **2 `mode:"control"`** (`STRUCTURED_TEXT`, pypdf metni dolu). `targets.json` her hedef için
`reason` (ör. `figure_and_equation`, `calendar_table`, `geometric_shape_grid`) ve `debug_excerpt` taşır.
Testler bunları zorunlu kılar: altı etkilenen soru tam olarak `{4,10,11,12,14,19}`,
kontrol soruları metin yolunda, image kayıtlarında `structured_text is None`.

### 7.5 Yardımcı araç karşılaştırması (pilot gözlemi)

| Araç | Sonuç |
|---|---|
| **PyMuPDF 1.28.2** | ✅ Resmî sayfayı 300 DPI kırptı; şekil/tablo/denklem yeniden kurulum olmadan korundu |
| **pypdf** | ❌ 6 soruda numara↔gövde yapısı kayboldu; Q14'te takvim hücreleri, Q19'da ölçü etiketleri dağıldı |
| **MinerU (flash tier)** | ⚠️ Blok türlerini ayırdı (text/image/equation/table) ama metni OCR düzleştirmesiyle bozdu: Q4/Q12'de `a2 + c2 = b2`, Q19'da `pr 2`. Yerel kurulumda resmî layout/table modelleri yok |

**Bu, task'ın "OCR/LLM nerede kullanılabilir" sorusunun doğrudan cevabıdır:** MinerU/PyMuPDF metni
`authoritative: false` ile işaretlenmiş ve pilot testleri bunu zorunlu kılar. **Hiçbir durumda
source-of-truth olmadılar.**

### 7.6 Görsel yüzeyin sınırı

PNG'ler `public/` altında olduğu için **statik olarak sunulabilir**; `app/pilot-2022-visual`
bunları `robots: noindex` ve `NEEDS_REVIEW` etiketiyle gösterir. Bu, bugün inceleme ekranı için
uygundur. Ancak kalıcı modele geçildiğinde bir görsel sorunun `stem`/`options` alanları
**kırpma görseliyle değiştirilirse**, `publish_verified.api_row` bugün yalnız `stem`+`options`
aktaracağı için görsel kayıp kalır. Bu, §15 `S-2`'nin gerekliliğinin nedenidir.

---

## 8. Candidate → Review → Verified → Published lifecycle

```
      ┌──────────┐  extract_pdf_candidates.py   ┌─────────────┐
      │  (PDF)   │ ───────────────────────────▶ │ NEEDS_REVIEW│  ← tek otomatik giriş noktası
      └──────────┘   status=NEEDS_REVIEW,        │ published=false
                     published=false              │ 11 kontrol: false
                                                   └──────┬──────┘
                                                          │ build_review_queue.py
                                                          ▼
                                                   ┌─────────────┐
                                                   │ review queue│  fingerprint + dup bayrakları
                                                   └──────┬──────┘
                                                          │ 👤 İNSAN: 11 kontrolü tek tek true
                                                          ▼
                                                   ┌─────────────┐
                                                   │  VERIFIED   │  ← yalnız validate_canonical.transition
                                                   └──────┬──────┘    (NEEDS_REVIEW'den, 11 kontrol true)
                                                          │ publish_verified.py
                                                          ▼
                                                   ┌─────────────┐
                                                   │  published  │  → data/questions/questions.json
                                                   └─────────────┘
                                                          │ GET /api/questions (yalnız doğrulanmış)
                                                          ▼
                                                        /calis  ← ⚠️ BAĞ YOK (bugün)
```

**Geçiş kuralları (`validate_canonical.transition`, hepsi testli):**

| Kural | Davranış |
|---|---|
| `VERIFIED`'a geçiş | **yalnız** `NEEDS_REVIEW`'dan |
| `VERIFIED` içeri | 11 kontrolün **tamamı** `true` olmalı |
| `VERIFIED` dışarı | terminal; yalnız `REJECTED`'a çıkılabilir |
| `NEEDS_REVIEW` içeri | yalnız `NEEDS_REVIEW`, `VERIFIED`, `REJECTED` |
| Yayın öncesi ek kapılar | `solution` boş olamaz; `booklet` boş olamaz; `question_number ≥ 1`; `answer ∈ {A,B,C,D}`; `answer.source_verified` **ve** `answer.answer_key_verified` **ayrı ayrı** `true`; en az **bir** curriculum katmanı kanıt bağlantısıyla `VERIFIED` |
| Yayın | `publish_verified.publish` her `VERIFIED` kaydı yeniden doğrular, **aynı fingerprint'li ikinci kaydı reddeder** |

**Doğrulanan fiili durum:** `data/questions/questions.json` = `[]`;
`scripts/.../published-pilot.json` = `[]`; `data/questions/review-queue.json` → `count: 0`.
Yani **bugün hiçbir soru yayınlanmamış** — kapılar çalışıyor, veri yok.

### 8.1 ⚠️ `F-3` — `validate_record` uyarıları incelemiyor

`validate_record` `extraction.warnings` alanına **hiç bakmıyor**. Bu nedenle 2022'deki
FEN Q16 (`option_boundary_ambiguous` — seçenek sınırları kaymış) ve FEN Q18
(`four_options_not_confidently_extracted` — `options: {}`) kayıtları, insan 11 kontrolü
doğru doldurursa `VERIFIED` olabilir. Bugünlük güvenlik, insanın `options_verified`
kontrolünü doğru doldurmasına bağlı. Uyarı→kapı bağı **yok**.

### 8.2 ⚠️ `F-4` — Repodaki pilot review queue bayat

`scripts/source-ingestion/data/questions/review-queue-pilot.json` **111 kayıt** içeriyor ve
`id` biçimi `MEB-LGS-2022:SAYISAL:Q01` (konu bileşeni yok). Mevcut staging'den yeniden
üretildiğinde ise **34 kayıt** ve `id` biçimi `MEB-LGS-2022:SAYISAL:MATEMATİK:Q01` çıkıyor
ve **0** kayıt duplicate-bayraklı. Yani bayat dosya, `id` şeması değişmiş eski bir çıktıdan
kalmış bir artefakt; mevcut staging'den yeniden üretilemiyor. Yanlışlıkla referans alınırsa
111 soruluk hayalet bir kuyruk okunur. **Kanıt:**
```
rebuild from CURRENT staging -> count=34  (first id …:MATEMATİK:Q01, dup-flagged: 0)
committed review-queue-pilot.json -> count=111  (first id …:SAYISAL:Q01)
```

---

## 9. `/api/questions` and `/calis` integration

### 9.1 `/api/questions` veri sınırı (doğrulandı — `route.ts` okundu + 3 sözleşme testi geçti)

**GET** — `validQuestion` filtresi bir kaydı ancak **hepsi** sağlanırsa kabul eder:

| Kapı | Koşul |
|---|---|
| Durum | `status === "VERIFIED"` |
| 11 kontrol | `REQUIRED_CHECKS.every(k => verification[k] === true)` |
| Yıl | `REAL_LGS` → `year ≥ 2018` |
| Kimlik | MEB türleri → `sourceId.startsWith("MEB-")`; `AI_GENERATED` → `sourceId.startsWith("AI-")`, tersi de zorunlu |
| Yapı | `grade===8`, `subject/stem` metin, `options` nesne, `answer ∈ options`, `solution` metin |
| Hash | `/^[a-f0-9]{64}$/` |
| Müfredat | `layer ∈ {LGS_REFERENCE_2018_PLUS, CURRENT_TYMM}` ve **6 alanın hepsi** dolu |

`toPublicQuestion` `{answer, verification, sourceHash}` alanlarını **çıkarır** → cevap anahtarı
istemciye gitmez. Yanıt başlığı `Cache-Control: no-store`.
**POST** — `timingSafeEqual` ile sunucu tarafında değerlendirme, yanıt **yalnız** `{correct: boolean}`.
Gerçek cevap asla dönmez. ✅ AGENTS.md "answer keys are server-side data" kuralı **karşılanıyor**.

### 9.2 ⚠️ `/calis` bugün bu veriyi görmüyor

`app/calis/page.tsx` yalnız `<StudyFlow />` render ediyor;
`components/study-flow.tsx` ise `import { questionBank } from "../data/content"` ile
**elle yazılmış demo soruları** kullanıyor (`grep -rn "api/questions" app components` → **boş**).

**Bugünkü haliyle:**
- `GET /api/questions` → `{ items: [], count: 0 }` (depo boş) **ve** UI bunu hiç çağırmıyor.
- `/calis` `data/content.ts`'teki demo bankayı gösteriyor; bu banka `Question` tipinde
  `correct: number` ve `explain` taşıyor ve `"use client"` bileşenine import ediliyor,
  yani **`correct` indeksi istemci paketinde**. Bu MEB verisi olmadığı için
  "MEB cevap anahtarı sızıntısı" **değildir**; ancak MEB soruları aynı yola alınırsa
  sızıntı olurdu. `/calis`'i MEB bankasına bağlamak bu nedenle §15 `S-3`'te bir güvenlik kapısıdır.

**Yanıt:** Evet, `/api/questions` yalnız doğrulanmış/yayınlanabilir veriyi gösterir — ve
`/calis` şu anda o veriye **hiç bağlı değildir**. Boşluk güvenlik açısından doğru yönde
(öğrenci MEB cevabını göremiyor), ama ürün açısından `/calis` hâlâ demo içerikle çalışıyor.

---

## 10. Validation gates

| # | Kapı | Nerede | Statü |
|---|---|---|---|
| G1 | Registry bütünlüğü (id benzersiz, tür, yıl ≥2018, MEB HTTPS host) | `validate_source_registry.py` | ✅ `npm run validate:sources` → "OK: 6 official source records" |
| G2 | Keşif kanıtı + redirect allowlist | `source_trust.py` | ✅ testli |
| G3 | SHA-256 + boyut + Content-Type + index URL eşleşmesi | `create_manifest`, `validate_manifest_for_pdf` | ✅ testli |
| G4 | Yapısal canonical geçerlilik | `validate_canonical.validate_record` | ✅ testli |
| G5 | **11 kontrolün tamamı `true`** | `validate_record(require_verified=True)` | ✅ testli |
| G6 | Yaşam döngüsü geçişi | `validate_canonical.transition` | ✅ testli |
| G7 | Yayın öncesi yeniden doğrulama + duplicate reddi | `publish_verified.publish` | ✅ testli |
| G8 | API sözleşmesi (status + 11 kontrol + alan soyma + `timingSafeEqual`) | `api-contract.test.mjs` | ✅ 3/3 geçti |
| G9 | Karantina (6 `REJECTED` manifest) | `test_manifest_quarantine.py` | ✅ testli |
| G10 | Görsel pilot bütünlüğü + cevap anahtarı sızıntısı yasağı | `test_visual_pilot.py` | ✅ 7 test geçti |
| **G11** | **Extraction uyarıları → yayın kapısı** | — | ❌ **YOK** (`F-3`) |
| **G12** | **Kitapçık uyumu (PDF başlığı ↔ `booklet`)** | — | ❌ **YOK** (`F-2`) |
| **G13** | **Konu başlığı kapsamı (`F-1`)** | kısmi | ⚠️ `ORPHAN_NUMBER` var, başlık kapsamı yok |

Bu tablo, task'ın "candidate ile published question arasında hangi validation kapıları var"
sorusunun cevabıdır: **10 kapı sağlam, 2'si eksik, 1'i kısmi.**

---

## 11. Failure / silent-loss scenarios

| # | Senaryo | Bugünkü davranış | Sessiz mi? | Durum |
|---|---|---|---|---|
| **F-1** | Ders başlığı `DİN KÜLTÜRÜ VE AHLAK BİLGİSİ` tanınmıyor | Soru **yanlış derse** atanır | 🔴 **EVET — sessiz bozulma** | Kanıtlı (§5.3) |
| **F-2** | `booklet` serbest metin, PDF başlığıyla karşılaştırılmıyor | A/B/C/D kitapçıklarda id + cevap anahtarı çakışması | 🔴 **EVET — sessiz** | Kanıtlı (§6.4) |
| **F-3** | `validate_record` `warnings[]` alanına bakmıyor | Bozuk seçenekli kayıt `VERIFIED` olabilir | 🟡 İnsana bağlı | Kanıtlı (§8.1) |
| **F-4** | `review-queue-pilot.json` bayat (111 vs 34) | Hayalet kuyruk okunabilir | 🟡 Yanlış referans riski | Kanıtlı (§8.2) |
| **F-5** | Tamamen taranmış/görüntü tabanlı PDF | `no_extractable_text_or_scanned_pdf` → 0 aday | ✅ **Sessiz değil** | Testli |
| **F-6** | Sayfa metin çıkarımı hatası | `page_text_extraction_error` + o sayfa boş | ✅ Sessiz değil | Testli |
| **F-7** | `candidate` ve `answer` aynı `answer_key` nesnesinde | İsim karışıklığı riski | 🟡 Adlandırma riski | OBSERVED |
| **F-8** | Hiç soru bulunamazsa | `no_question_candidates_detected`; 0 ≠ başarı | ✅ Sessiz değil | Testli |
| **F-9** | Cevap anahtarı belirsiz | `answer_key_evidence_ambiguous` + `diagnostics` | ✅ Sessiz değil | Testli |
| **F-10** | Aynı PDF farklı byte ile yeniden indirilirse | Hash çakışması → **hata** | ✅ Sessiz değil | Testli |
| **F-11** | Geçersiz PDF (sertifika) | `REJECTED` manifest + karantina testi | ✅ Sessiz değil | Testli |
| **F-12** | Aynı fingerprint'li iki `VERIFIED` kayıt | `publish` reddeder | ✅ Sessiz değil | Testli |
| **F-13** | Alt kırpmada görsel kayıp | `publish_verified` yalnız stem/options taşır | 🔴 **EVET** | §7.6, `S-2` |

**En tehlikelisi F-1 ve F-2'dir**, çünkü ikisi de mevcut test paketinin **kör noktasında**
(yalnız Sayısal kitapçık işlendiği için) duruyor ve ikisi de "sessiz kayıp" değil,
**"sessiz olarak yanlış veri üretme"** biçiminde. Bir kayıp en azından `review_reasons`'a düşer;
yanlış etiketli/yanlış kitapçıklı veri ise akıcı görünür.

---

## 12. 2022 pilot findings

**Çalışan, kanıtlanmış ve korunması gerekenler:**

1. Provenance zinciri (keşif → redirect → SHA-256 → manifest → çıkarım) **uçtan uca** çalışıyor.
2. Çıkarım **deterministik**: PDF yeniden okundu, 34/34 kayıt birebir aynı üretildi.
3. Cevap anahtarı eşleştirmesi **konuya duyarlı ve reddedici**: MAT Q20=`B`, FEN Q20=`D`,
   diagnostics boş, `unmapped=0`, `conflicts=0`.
4. Altı görsel soru **tümü** kayıt altında: `unparsed_question_numbers` dolu, `review_reasons`'da
   `question_numbers_without_text_block` var.
5. Görsel temsil **yeniden üretilebilir** (8/8 crop rect + piksel eşleşti).
6. Hiçbir katman `VERIFIED`/`published` değil; `answer` 34/34 `null`; `solution` 34/34 `null`.
7. Karantina ve duplicate koruması çalışıyor.

**Öğrenilen dersler (2022'ye özgü olmayanlar):**

| Ders | Kanıt |
|---|---|
| pypdf şekil/tablo/grafik/denklem içeren sorularda numara↔gövde yapısını kaybediyor | 6 soru |
| Şekil/tablo içeren soru için **hiçbir metin yöntemi** güvenilir değil; raster kırpma tek güvenli yol | MinerU'nun `a2 + c2 = b2` bozulması |
| Basit tablolar (Q6, Q13) metin olarak **okunabiliyor** → hibrit model gerekçeli | 2 kontrol sorusu `STRUCTURED_TEXT` |
| `parse_options` kaymış sınırları tespit edebiliyor ama **reddetmiyor**, sadece uyarıyor | FEN Q16 |
| Tam çıkarılamayan seçenekler `{}` bırakılıyor (uydurma yok) ama kayıt yine de üretiliyor | FEN Q18 |

**Pilotun kanıtlamadığı şeyler (dürüstlük notu):**
- Tek ders bile sözel kitapçık **işlenmedi** → konu başlığı çeşitliliği test edilmedi (**F-1** gizli).
- Tek kitapçık harfi (**A**) işlendi → çok kitapçık kimliği test edilmedi (**F-2** gizli).
- `VERIFIED` yolu **gerçek veriyle hiç çalıştırılmadı** — `questions.json` hâlâ `[]`.
- Hiçbir DB bağlantısı yok; `db/001_question_bank.sql` uygulanmadı.

---

## 13. Scalability requirements for 2018–2026

### 13.1 Kayıt defteri bugün neyi kapsıyor?

| Yıl | Registry | Gerçek PDF | Kitapçık kodları |
|---|---|---|---|
| 2018–2021 | ❌ **YOK** | — | — |
| 2022 | ✅ `MEB-LGS-2022` | ✅ Sayısal A | `SAYISAL`, `SOZEL` (harfsiz) |
| 2023 | ✅ `MEB-LGS-2023` | ❌ (yalnız karantina) | `SAYISAL`, `SOZEL` |
| 2024 | ✅ `MEB-LGS-2024` | ❌ (yalnız karantina) | `SAYISAL`, `SOZEL` |
| 2025 | ✅ `MEB-LGS-2025` | ❌ (yalnız karantina) | `SAYISAL_A`…`SAYISAL_D` |
| 2026 | ✅ `MEB-LGS-2026` | ❌ (yalnız karantina) | `SAYISAL_A`…`SAYISAL_D` |
| Örnek sorular | ✅ `MEB-SAMPLE-ARCHIVE` | ❌ (yalnız karantina) | 7 dönem |

Yani "2018–2026" hedefinin bugünkü gerçek kapsamı: **1 yıl, 1 kitapçık, 1 bölüm (Sayısal).**

### 13.2 Ölçeklenme gereksinimleri

| Gereksinim | Neden | Bugünkü durum |
|---|---|---|
| **R1 — Kitapçık kimliği birincil olmalı** | 2025/2026'da A–D kitapçıkları farklı soru sırası **ve** farklı cevap anahtarı taşır | ❌ `F-2` |
| **R2 — Ders başlığı sözlüğü MEB'in resmî başlıklarının tamamını kapsamalı** | SÖZEL kitapçıklar `DİN KÜLTÜRÜ VE AHLAK BİLGİSİ` içerir | ❌ `F-1` |
| **R3 — SÖZEL bölüm desteği** | 8 yılın yarısı sözel bölüm; bugün hiç denenmedi | ❌ |
| **R4 — Yıllara göre düzen farkı toleransı** | 2018–2021 kitapçıkları 2022 sonrasından farklı görsel şablon kullanır | ⚠️ bilinmiyor |
| **R5 — Çok kitapçıklı toplu işleme + çapraz doğrulama** | A/B/C/D'nin **aynı soruyu farklı yerleştirdiği** bilinir; bu, karşılıklı doğrulama için fırsattır | ❌ |
| **R6 — Beklenen soru sayısı mutabakatı** | Bölüm başına 20 soru; 14 çıkması **kendiliğinden** yakalanmalı | ⚠️ kısmi (`ORPHAN_NUMBER`) |
| **R7 — Kayıt defterinin 2018–2021'i kapsaması** | Politika 2018'den başlıyor, veri 2022'den başlıyor | ❌ |
| **R8 — Depolama ölçeği** | 8 yıl × 4 kitapçık × 40 soru ≈ 1.280 aday + raster kırpmalar | ⚠️ 1,2 MB/6 soru → tahmini **~250 MB** |

### 13.3 ⚠️ `F-5` — Beklenen soru sayısı mutabakatı yok

Bölüm başına 20 soru olduğu cevap anahtarından bilinebilir (MATEMATİK 20, FEN 20). Bugün kod,
**cevap anahtarında olup soru kaydı üretilemeyen** numaraları raporlamıyor
(`answer_key_summary` yalnız `unmapped_candidates` = kaydı olup anahtarı olmayanı sayar).
2022'de 40 anahtar − 34 kayıt = **6 eksik**, yalnızca `ORPHAN_NUMBER` deseninin tesadüfüyle görüldü.
Farklı bir düzen bu desene uymazsa **eksik hiç raporlanmaz**.

---

## 14. Recommended target architecture

Mevcut mimariyi **bozmadan** genişleten öneri (kod değişikliği değil, hedef tasarım):

```
                    ┌─────────────────────────────────────────────┐
                    │  1. SOURCE LAYER (değişmezlik garantili)     │
                    │  registry → discover → download → manifest   │
                    │  • SHA-256 + redirect + allowlist (mevcut)   │
                    │  + kitapçık kimliği PDF'ten TÜRETİLİR  (yeni)│
                    │  + kaynak defteri 2018–2021 ile doldurulur   │
                    └───────────────────────┬─────────────────────┘
                                            ▼
        ┌───────────────────────────────────────────────────────────┐
        │  2. REPRESENTATION ROUTER  (yeni karar katmanı)            │
        │  Soru başına ölçüt: "birincil temsil metin mi, raster mı?" │
        │  ölçüt: pypdf bloğu + seçenek bütünlüğü + şekil/vektör     │
        │  → STRUCTURED_TEXT | IMAGE_BACKED | HYBRID(metin+kırpma)   │
        └───────────────────────┬───────────────────────────────────┘
                                ▼
   ┌────────────────────────────┴──────────────────────────────────┐
   │ 3. STRUCTURED CONTENT        │ 4. VISUAL CONTENT               │
   │ stem + A-D options           │ orijinal sayfa raster kırpma    │
   │ (pypdf; uyarılar kapı)       │ (PyMuPDF 300 DPI; PDF değişmez) │
   └────────────────────────────┬──────────────────────────────────┘
                                ▼
        ┌───────────────────────────────────────────────────────────┐
        │  5. OFFICIAL ANSWER KEY  (candidate → insan → answer)      │
        │  + kitapçık harfi eşleşme kapısı                     (yeni)│
        │  + anahtar↔soru mutabakatı (20/20)                   (yeni)│
        └───────────────────────┬───────────────────────────────────┘
                                ▼
        ┌───────────────────────────────────────────────────────────┐
        │  6. NÜLİ SOLUTION  (yeni alan; MEB verisinden AYRI)        │
        │  • kaynak: HEURISTIC | AI_GENERATED | HUMAN               │
        │  • solution.ai_generated = true ise ASLA MEB diye sunulmaz │
        └───────────────────────┬───────────────────────────────────┘
                                ▼
        ┌───────────────────────────────────────────────────────────┐
        │  7. NÜLİ PEDAGOGICAL ANALYSIS (yeni; iki müfredat katmanı) │
        │  tema/ünite/kazanım/beceri + H1–H7 + zorluk               │
        │  • evidence_url zorunlu; VERIFIED olmadan yayın yok        │
        └───────────────────────┬───────────────────────────────────┘
                                ▼
              review queue → validate → publish → /api/questions → /calis
```

**Değişmeyen ilkeler:**
- `MEB SOURCE` (PDF) **tek** source-of-truth'tur; OCR/LLM hiçbir katmanda onun yerini almaz.
- Aday katmanları (`candidate`) ile doğrulanmış katmanlar (`answer`, `solution`, pedagoji)
  farklı alanlar ve farklı geçiş kapılarıdır.
- `VERIFIED` yalnız insan kararıyla, 11 kontrolle verilir.

## 15. Minimal required schema changes, if any

**Önce mevcut şema sınırı (kanıtlı):** `canonical_schema.json` (`schema_version:"1.0"`) dört alt nesneyi
**kapalı** tutar (`additionalProperties:false`): `source`, `question`, `answer_key`, `curriculum`,
`mapping`. `extraction` ve `checks` ise ek alan kabul eder. Bir alan eklemenin maliyeti bu yüzden
iki sınıfa ayrılır:

| Sınıf | Nesneler | Alan eklemenin maliyeti |
|---|---|---|
| **Kapalı** | `source`, `question`, `answer_key`, `curriculum`, `mapping` | Şema dosyası **güncellenmeli**; aksi halde kayıt `additionalProperties:false` ile geçersiz olur |
| **Açık** | `extraction`, `checks` | Şema dosyası değişmez; yalnız tüketici kod/kontrat güncellenir |

**Ölçülen minimum:** Bugünkü 2022 boru hattı yalnız **metin** soruları ürettiği ve bunlar mevcut şemaya
sığdığı için **çalışır durumda kalmak adına zorunlu bir şema değişikliği yoktur.** Aşağıdaki
`S-1`…`S-7`, *hedef mimariye geçiş* içindir; her biri bir bulguya bağlıdır ve sınıf/öncelik taşır.

| ID | Alan / değişiklik | Şema sınıfı | Bağlı | Neden gerekli |
|---|---|---|---|---|
| **S-1** | `source.booklet_evidence` (veya `extraction.booklet_evidence`) + `booklet_mismatch` review reason | Kapalı (`source`) / Açık (`extraction`) | F-2 (§6.4) | `booklet` serbest metindir; PDF'in `“A” KİTAPÇIĞI` başlığıyla karşılaştırılmazsa A/B/C/D karışır. Kanıt alanı olmadan uyumsuzluk üretilemez |
| **S-2** | `question.visual: {asset_path, sha256, clip_rect_pt, render_dpi, authority:"ORIGINAL_MEB_PDF", reconstructed_from_ocr:false} \| null` **+** `publish_verified.api_row` → `visual` **+** `Question` tipi | Kapalı (`question`) | F-13 (§7.6) | Bugün görsel sorunun görseli yalnız `pilot.json`'da; canonical şemada ve yayın satırında **karşılığı yok** |
| **S-3** | Kod değil sözleşme: MEB bankası `/calis`'e bağlanmadan önce "cevap anahtarı istemciye gitmez" kapısı | — (yayın/UI sözleşmesi) | §9.2 | `/calis` bugün `data/content.ts`'te `correct` indeksini istemci paketine koyan bir demo banka kullanıyor; MEB verisi aynı yola alınırsa sızıntı olur |
| **S-4** | `api_row` + `Question.curriculum.evidenceUrl` | Kapalı değil (yayın/API şeması) | §3.3 | `evidence_url` canonical'da var, yayın satırında **yok** → provenance zinciri yayın noktasında kopuyor |
| **S-5** | `solution` düz `string` yerine provenance'lı nesne (`{text, source: HUMAN\|AI_GENERATED\|HEURISTIC, verified}`) **veya** `extraction.solution_source` | Kapalı (`solution` şemada tipli) / Açık (`extraction`) | Nüli çözüm ayrımı (§6.2) | Bugün `solution` boş; Nüli çözümünü MEB verisinden ayıran **kaynak alanı yok** |
| **S-6** | `answer_key` ad ayrımı: `official_candidate` / `verified_answer` (en azından dokümante) | Kapalı (`answer_key`) | F-7 (§6.2) | `candidate` ve `answer` aynı nesnede; karıştırılma riski |
| **S-7** | `checks.extraction_warnings_cleared: boolean` | Açık (`checks`) | F-3 (§8.1) | Uyarı→kapı bağı yok; FEN Q16/Q18 bugün insan kaprisiyle `VERIFIED` olabilir |

**S-7 için ek senkron yükü (kanıtlı):** `checks` şeması ek alan kabul etse de "zorunlu kontrol" listesi
**üç ayrı yerde** yazılıdır ve senkron tutulmalıdır: `validate_canonical.py:13` (`REQUIRED_CHECKS`),
`app/api/questions/route.ts:10` (`REQUIRED_CHECKS`), `canonical_schema.json` (`checks.required`).
Bugün üçü de aynı **11** anahtarı taşır; yeni bir kontrol eklenirse üçünün birlikte güncellenmesi
gerekir, aksi halde staging doğrulaması ile API sözleşmesi sessizce ayrışır.

**S-2'nin şema kanıtı — F-13'ten daha ağır bir sonuç:** `validate_record`
(`validate_canonical.py:58-60`) her kayıtta **dolu `stem`** ve **tam olarak `{A,B,C,D}` dolu seçenek**
ister — `require_verified` olmasa bile. `question` kapalı olduğu için görsel alan da eklenemez.
`publish_verified.api_row` yalnız `stem`+`options` aktarır. Dolayısıyla bugünkü şemayla:
**`structured_text: null` olan bir `mode:"image"` kaydının canonical karşılığı yoktur ve
`/api/questions`'a ulaşabileceği bir kanal bulunmamaktadır.** Yani `F-13` "yayında görsel düşüyor"
değil, daha güçlü olarak "**görsel temsilin şemada ve yayın yolunda hiçbir karşılığı yok**"tur.
Bu tek başına, 2022 görsel pilotunun ürün hedefi için S-2'yi zorunlu kılar.

---

## 16. Migration/implementation phases

Bu fazlar **uygulanmamış** önerilerdir (bu görev kod değiştirmez). Her faz mevcut davranışı bozmaz,
`NEEDS_REVIEW` durumunu değiştirmez ve **kendiliğinden `VERIFIED` üretmez.** Sıralama, düzeltmenin
"sessiz olarak yanlış veri üretme" yüzeyini ne kadar azalttığına göredir.

| Faz | ID | İş | Bağlı | Öncelik | Bağımlılık |
|---|---|---|---|---|---|
| A | **T-1** | `SUBJECT_HEADERS`'ı tam başlık eşlemesine geçir (`DİN KÜLTÜRÜ VE AHLAK BİLGİSİ` → `DİN KÜLTÜRÜ`) **ve** tanınmayan başlıkta `NO_SUBJECT_HEADER` review reason üret | F-1 | **P0** | — |
| A | **T-2** | Kitapçık kanıtı: PDF metninden kitapçık kimliğini oku, `booklet_evidence` yaz, `source.booklet` ile uyuşmazsa `booklet_mismatch` review reason üret | F-2 / S-1 | **P0** | — |
| B | **T-3** | Uyarı→kapı: `extraction.warnings` boş değilse `extraction_warnings_cleared=false`; `REQUIRED_CHECKS`'e ekle (üç yerde senkron) | F-3 / S-7 | P1 | — |
| B | **T-4** | Beklenen soru sayısı mutabakatı: cevap anahtarı sayısı (20/20) ile üretilen kayıt sayısını karşılaştır; eksikse `missing_question_numbers` raporla | F-5 / R6 | P1 | T-1 (doğru konu etiketi) |
| B | **T-5** | Bayat `review-queue-pilot.json` (111 kayıt, eski `id` biçimi) arşivle veya yeniden üret (34 kayıt, yeni `id`) | F-4 | P1 (küçük) | — |
| C | **T-6** | Görsel temsil köprüsü: `question.visual` + `api_row.visual` + `Question` tipi ile görsel soruları yayın yoluna aç; `/calis` bağlantısı için S-3 kapısını uygula | F-13 / S-2 / S-3 | P1 (**PO kararı**) | S-3 ürün kararı |
| D | **T-7** | Provenance hijyeni: `evidence_url` yayına (S-4), `answer_key` ad ayrımı (S-6), `solution` provenance (S-5) | §3.3 / F-7 | P2 | T-6 ile birlikte anlamlı |
| D | **T-8** | Kayıt defterine 2018–2021 kaynaklarını ekle | R7 / P-1 | P2 (veri hazırlığı) | PO kararı |

**Faz mantığı:**
- **Faz A (P0, bozulma önleyici):** T-1 ve T-2 küçük, izole ve testlidir; ikisi de *sessiz yanlış veri*
  üretimini keser. Sözel kitapçık veya B/C/D kitapçık işlenmeden **önce** yapılmalıdır.
- **Faz B (P1, bütünlük):** T-3/T-4 mevcut artefaktın kendi kapılarından geçmesini sağlar (bkz. §17
  `R10`), T-5 kafa karıştıran bayat artefaktı ortadan kaldırır.
- **Faz C (P1, ürün kararı):** T-6 olmadan görsel pilotun ürün hedefi teknik olarak gerçekleşemez.
- **Faz D (P2, hijyen/ölçek):** T-7/T-8 veri büyümeden önce yapılmalıdır.

**TASK PROPOSAL (istenen biçim):**

| TASK PROPOSAL | Reason | Scope | Dependency | Priority |
|---|---|---|---|---|
| `SUBJECT_HEADERS` tam eşleme + `NO_SUBJECT_HEADER` | F-1: sözel kitapçıkta sessiz yanlış ders etiketi | `extract_pdf_candidates.py` (SUBJECT_HEADERS, segment_lines, review_reasons) + test | — | P0 |
| Kitapçık kanıtı + `booklet_mismatch` | F-2: A/B/C/D cevap anahtarı çakışması | `extract_pdf_candidates.py`, `canonical_schema.json` (S-1), test | — | P0 |
| Uyarı→yayın kapısı | F-3: bozuk seçenekli kayıt `VERIFIED` olabilir | `validate_canonical.py`, `app/api/questions/route.ts`, `canonical_schema.json` (S-7), test | — | P1 |
| Beklenen soru sayısı mutabakatı | F-5/R6: eksik soru kendiliğinden yakalanmıyor | `extract_pdf_candidates.py` review çıktısı + test | T-1 | P1 |
| Bayat pilot review queue temizliği | F-4: 111 vs 34 hayalet kuyruk | `scripts/source-ingestion/data/questions/review-queue-pilot.json` | — | P1 |
| Görsel temsil yayın köprüsü + `/calis` kapısı | F-13/S-2/S-3: görsel soruların yayın kanalı yok | `canonical_schema.json`, `publish_verified.py`, `app/api/questions/route.ts`, `components/study-flow.tsx` | PO kararı (PD-1, PD-6) | P1 |
| Provenance hijyeni (evidence_url, answer adı, solution kaynağı) | §3.3/F-7: yayında provenance kesiliyor | `publish_verified.py`, `app/api/questions/route.ts`, `canonical_schema.json` | T-6 | P2 |
| 2018–2021 kaynak kaydı | R7/P-1: "2018–2026" hedefi veri olarak imkânsız | `data/source-engine/config/source-registry.json` | PO kararı (PD-2) | P2 |

---

## 17. Risks and unresolved PO decisions

### 17.1 Çözülmemiş PO kararları (uygulamayı doğrudan bloke eder)

| ID | Karar | Neden PO'ya ait | Varsayılan (karar verilmezse) |
|---|---|---|---|
| **PD-1** | Görsel sorularda birincil temsil ne olacak: yalnız raster mı, yoksa **hibrit** (metin gövde + görsel alan) mı? | Şemayı (S-2) ve yayın satırını doğrudan belirler; "sessiz şema kararı" verilmemeli | Pilot `mode:"image"` (structured_text null) + kontrol soruları metin |
| **PD-2** | Sıra: 2022'yi tamamlamak mı, 2018–2021 kaynağını bulmak mı, yoksa 2023–2026'yı çekmek mi? | Kaynak kapsamı ve ölçek riski (R7, R8) | 2022 tek yıl kalır |
| **PD-3** | Nüli çözümü kim üretir: insan mı, AI mı? AI ise hangi etiketleme zorunlu? | Provenance/pedagoji politikası; S-5'in şekli buna bağlı | `solution` boş kalır |
| **PD-4** | Kalıcılık: statik JSON mu, `db/001_question_bank.sql` uygulanmış DB mi? | Mimari karar; ölçekte JSON sorgulanamaz | JSON statik (bugünkü hâl) |
| **PD-5** | Çok kitapçık stratejisi: A–D ayrı soru kaydı mı, yoksa tek soru + karşılıklı doğrulama mı? | Kimlik şemasını (S-1) ve ölçeği belirler | Her kitapçık ayrı işlenir; kimlik çakışır (F-2) |
| **PD-6** | Görsel assetler `public/` altında statik mi kalacak, yoksa yetkili bir yoldan mı sunulacak? | Telif/KVKK/erişim kararı | `public/pilot-2022-visual/` statik (noindex) |
| **PD-7** | `answer_key` alan adları değişecek mi (S-6) yoksa yalnız dokümante mi edilecek? | Kırıcı şema değişikliği; mevcut artefaktları etkiler | Değişmez (F-7 riski kalır) |

### 17.2 Riskler (R1–R8 §13'te; aşağıdakiler bu analizde **yeni** ölçülenlerdir)

| ID | Risk | Kanıt | Ciddiyet |
|---|---|---|---|
| **R9** | **Görsel soruların canonical karşılığı yok** — şema dolu `stem` + 4 dolu seçenek ister; `question` kapalı; `api_row` görsel taşımaz | `validate_canonical.py:58-60`, `canonical_schema.json`, `publish_verified.py:10-21` | 🔴 Yüksek (ürün hedefini bloke eder) |
| **R10** | **Gerçek 2022 staging dosyası kendi yapısal kapısından geçmiyor** | `python3 validate_canonical.py …SAYISAL.json` → **exit 1**: `FEN:Q15`, `FEN:Q18` "exactly four non-empty A-D options are required" | 🟠 Orta (spec §10'daki "G4 ✅" ifadesi gerçek artefakt için geçerli değil) |
| **R11** | Duplicate fingerprint yalnız `stem`+`options` kullanır; kitapçık/görsel/kaynak dahil değil | `build_review_queue.fingerprint:12-20` | 🟡 Düşük–Orta (görsel sorular metin gövdesiz olursa boş `stem`+boş `options` çakışabilir) |
| **R12** | Görsel asset ölçeği ve sunum maliyeti: 6 soru ≈ 1,2 MB → 8 yıl × 4 kitapçık × 40 soru ≈ **~250 MB** | §7.3, §13.2 (`R8`) | 🟠 Orta |
| **R13** | Kalıcılık kararı uygulanmamış: `db/001_question_bank.sql` repoda duruyor, **uygulanmamış**; statik JSON sorgulanamaz | §1 tablo (satır 9–10), §3.2 | 🟠 Orta (PD-4 ile ilişkili) |
| **R14** | "2018–2026" hedefi bugün **veri olarak imkânsız**: registry 2018–2021'i içermiyor, diğer yıllar yalnız karantinada | §13.1, `source-registry.json` (yalnız `MEB-LGS-2022`…`2026` + örnek arşiv) | 🟠 Orta (PD-2 ile ilişkili) |

### 17.3 Privacy / security açısından açık noktalar

- **Cevap anahtarı sunucu tarafı:** bugün doğru (`toPublicQuestion` `answer`/`verification`/`sourceHash`
  çıkarır; POST `timingSafeEqual`). Ancak `/calis` demosu `correct` indeksini istemci paketine koyar
  (§9.2). MEB bankası bu yola alınırsa **kapı zorunludur** (S-3/T-6).
- **Öğrenciye görsel sunumu:** orijinal MEB sayfasının raster kırpması öğrenciye gösterildiğinde telif
  ve KVKK değerlendirmesi gerekir (PD-6). Bu spec yalnız inceleme ekranını (noindex) kapsar.
- **Ham PDF'ler ve kırpmalar** provenance kanıtıdır; `archive/` immutable, `manifests/` SHA-256'lı.

### 17.4 Kabul edilen sınırlar (scope honesty)

- Bu analiz **kod değiştirmedi**; T-1…T-8 uygulanmadı, hiçbir kayıt `VERIFIED`/`published` yapılmadı.
- Kapsam **2022 Sayısal A, tek kitapçık, tek bölüm**tür; sözel ve çok kitapçık **hiç denenmedi** (F-1, F-2).

---

## Ek — Doğrulama kaydı (TASK-QBANK-004 devam koşusu)

Spec'in ilk yazımı 2026-10-04 15:11–15:20 arasında sağlayıcı soket hatasıyla
(`run_result.finishReason:"error"`, iteration 25) yarıda kesildi; §0–§14 yazılmış, §15–§17 eksik kalmıştı.
Bu bölüm, spec'in **devam koşusunda** tamamlanmasıyla birlikte yapılan doğrulama ve twin-check kaydıdır.

**Çalıştırılan komutlar ve gözlenen sonuçlar:**

| Komut | Sonuç |
|---|---|
| `npm run validate:sources` | `OK: 6 official source records` |
| `npm run test:source` | `Ran 91 tests … OK` + node `api-contract` **3/3 pass** (`exit=0`) |
| `python3 validate_canonical.py …/MEB-LGS-2022__SAYISAL.json` | **exit 1** — `FEN:Q15`, `FEN:Q18` (bkz. R10) |
| staging özeti (python, read-only) | 34 kayıt · `candidate` 34/34 dolu · `answer` **34/34 null** · `solution` **34/34 null** · hepsi `NEEDS_REVIEW` · `booklet` hepsi `"SAYISAL"` · curriculum hepsi `UNMAPPED` · `unparsed_question_numbers` = [4,10,11,12,14,19] · `published=false` |
| `data/questions/questions.json` | `[]` |
| `review-queue-pilot.json` | `count: 111`, ilk `record_id = MEB-LGS-2022:SAYISAL:Q01` (F-4 doğrulandı) |
| `source-registry.json` | 2025/2026 kitapçıkları `SAYISAL_A…SAYISAL_D` (F-2 riski doğrulandı) |

**Twin-check (bağımsız yeniden üretim):**
- **F-1:** gerçek `segment_lines()` sentetik bir akışla (başlıklar `TÜRKÇE` → `SOSYAL BİLGİLER` →
  `DİN KÜLTÜRÜ VE AHLAK BİLGİSİ`) yeniden çalıştırıldı. Sonuç: **3 blok**; üçüncü soru
  `subject='SOSYAL BİLGİLER'` olarak etiketlendi. `"DİN KÜLTÜRÜ VE AHLAK BİLGİSİ" in SUBJECT_HEADERS`
  → **False**. → **F-1 bağımsız olarak doğrulandı.**
- **F-5 (cevap anahtarı):** harness çıktısı `MATEMATİK 20`, `FEN BİLİMLERİ 20`, `diagnostics []`,
  `unmapped_candidates=0`, `subject_conflicts=0`; spec §6.1 ile birebir uyumlu.

**Spec'e düzeltme (erratum):** §10 tablosundaki `G4 — Yapısal canonical geçerlilik ✅ testli` ifadesi
**test paketi** için doğrudur, ancak **gerçek 2022 staging artefaktı** için değildir: gerçek dosya
`validate_canonical.py`'dan 2 hata ile döner (R10). Bu, "10 kapı sağlam" özetini
"**9 kapı sağlam, G4 gerçek veride kırmızı, 2 kapı eksik (G11/G12), G13 kısmi**" olarak düzeltir.

<!-- APPEND-MARKER -->

---

## Ek II — TASK-QBANK-005 uygulama kaydı (2026-10-05)

**Sonuç:** `VERIFIED WITH CAVEATS` (aşağıdaki gerekçelerle).

### R9 — canonical görsel temsil

| Katman | Değişiklik |
|---|---|
| `canonical_schema.json` | `question.representation` (`STRUCTURED_TEXT` \| `IMAGE_BACKED` \| `HYBRID`, **opsiyonel** → geriye uyum) + `question.visual` (`null` \| `$defs/visual`). `$defs/visual` `authority: const ORIGINAL_MEB_PDF`, `reconstructed_from_ocr: const false`, `asset_sha256` (SHA-256), `page`, `clip_rect_pt`, `render_dpi ≥ 150`. `stem`/`options` artık `null` olabilir (yalnız görsel temsilde). |
| `validate_canonical.py` | `validate_structure()` temsil moduna göre çalışır: `STRUCTURED_TEXT`/`HYBRID` → dolu gövde + tam dört dolu A-D; `IMAGE_BACKED`/`HYBRID` → kanıtlı `visual` bloğu zorunlu. `validate_visual()` provenance zincirini doğrular. Görselin kendisi **kanıt sıfırlamaz**: eksik option seti `IMAGE_BACKED` altında da reddedilir. |
| `publish_verified.py` | `api_row` → `representation` + `visual{publicPath, page, clipRectPt, renderDpi, authority}`. `asset_path`/`asset_sha256` **yayınlanmaz**. |
| `app/api/questions/route.ts` | `Question` tipi genişletildi; `validVisual()` aynı traversal/authority kurallarını uygular. Cevap anahtarı `toPublicQuestion` ile sunucuda kalır. |

**Güvenlik:** `safe_asset_path()` her path segmentini ayrı denetler; `../`, `a/../b.png`,
`/etc/passwd.png`, `..png` reddedilir. Mutlak yol ve `//` prefix reddedilir (arbitrary file
serving yüzeyi yok). Görsel `public/` altında statiktir ve pilot route `noindex` kalır.

### R10 — 2022 yapısal kapı

| Kayıt | Bulgu | Sonuç |
|---|---|---|
| `MEB-LGS-2022:SAYISAL:FEN:Q15` | A–D anahtarları tam, **`D: ""`** boş | `question options present but empty: D` |
| `MEB-LGS-2022:SAYISAL:FEN:Q18` | `options: {}` — hiç seçenek yok | `question options are missing A-D keys: A, B, C, D` |

İki hata artık **tek genel mesaj yerine ayrı ayrı** raporlanır. `extract_pdf_candidates`
boş option value'yu de çıkarım anında `option_value_empty` uyarısıyla işaretler (Q15 artık
`confidence: LOW`).

**Neden düzeltilmedi:** pypdf metin katmanı Q15'in işaret-tablo seçeneklerini ve Q18'in
tablo hâlindeki seçeneklerini vermiyor. Tahmini seçenek/cevap üretmek yasak. Bu nedenle
kayıtlar **açık validation failure** olarak, `NEEDS_REVIEW` + `answer: null` +
`published: false` durumunda bırakıldı. `transition(→VERIFIED)` her ikisini de reddeder.

### Doğrulama (çalıştırıldı)

| Komut | Sonuç |
|---|---|
| `npm run validate:sources` | `OK: 6 official source records` |
| `npm run test:source` | `Ran 105 tests … OK` (91 → 105; yeni `test_visual_representation.py` 14 test) + api-contract 3/3 |
| `npm run test:taxonomy` | 5/5 pass |
| `npm run test:ai` | 19/19 |
| `npx tsc --noEmit` | exit 0 |
| `git diff --check` | exit 0 |
| `validate_canonical.py` (gerçek artefakt) | **exit 1** — Q15 + Q18, beklenen ayrı hatalar |
| `npm run build` | **exit 1** — `/_global-error` prerender hatası. **Bu değişiklikten bağımsızdır**: `route.ts` stash'lenerek yeniden denendi ve değişiklik olmadan da aynı hata oluştu. Önceden var olan kırık durumdur. |

### Twin-check (4 bağımsız eksen)

1. Gerçek artefit doğrudan incelendi: Q15 `empty=['D']`, Q18 `keys=[]`, ikisi de `NEEDS_REVIEW`/`LOW`.
2. **Gerçek pilot crop kaydı** (`pilot.json` Q04'ten, gerçek `clip_rect_pt`/`page`/yol ile)
   canonical kayda dönüştürüldü → `validate_record` → `[]` (geçerli). Sentetik `STRUCTURED_TEXT`
   karşılaştırması da `[]` → iki temsil de kanıtla temsil edilebiliyor.
3. Karşılaştırmalı kontrol: aynı temel kayıt `STRUCTURED_TEXT` → `visual: null`;
   `IMAGE_BACKED` → `visual.publicPath` dolu; traversal varyantı → reddedildi.
4. Sızıntı: `data/questions/questions.json` = `[]`; `publish()` gerçek artefaktta `[]` döndü;
   `NEEDS_REVIEW` kayıt yayına giremiyor; `/calis` `data/content.ts` demo bankasından besleniyor.

### Açık riskler

- `npm run build` bu görevden önce kırık (yukarıda kanıtlandı); düzeltilmedi.
- `pilot-2022-visual` route hâlâ `structured_text`/`mode` alanlarını okuyor; canonical
  `representation`/`visual` alanlarıyla **eşleştirilmemiştir** (kapsam dışı bırakıldı).
- `answer_key` ad ayrımı (S-6), `solution` provenance (S-5), `evidence_url` yayına (S-4) ve
  uyarı→kapı bağı (S-7) hâlâ açık; bu görev kapsam dışıydı.