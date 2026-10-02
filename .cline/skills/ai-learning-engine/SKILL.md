---
name: ai-learning-engine
description: Nüli (LGS AI Coach) AI çıktı katmanı işleri için proje-özgü kurallar. /api/ai sözleşmesi, model yanıtının doğrulanabilir structured data'ya dönüşmesi, H1–H7 enum, confidence, müdahale önerisi, halüsinasyon/kaynak uydurma önleme ve provider hata temizliği değişikliklerinde kullan.
---

# ai-learning-engine

AI'ın öğrenciye gösterdiği her metin ya da veri **doğrulanabilir olmalı**.

## Yetkili kaynak

**`AGENTS.md` → "AI providers and secret handling"** ve **"Error taxonomy: H1–H7"**.

## Bugünkü gerçek durum (uydurma)

- `POST /api/ai` sözleşmesi serbest metindir: `{ answer, provider, model }`. Hata halinde
  `{ error, attempts[] }` (502) veya `{ error }` (400/413/5xx) döner.
- Yapılandırılmış alanlar (`error_type`, `confidence`, `intervention`, …) **henüz yoktur**.
- Structured çıktı bir görevde istendiğinde: sözleşme **sunucuda** doğrulanmalı, doğrulanamayan
  yanıt kullanıcıya olduğu gibi gösterilmemeli, hata olarak işaretlenmelidir.

## Hedef şema (önerilen, uygulanmamış)

```jsonc
{
  "error_type": "H1|H2|H3|H4|H5|H6|H7|UNKNOWN",  // enum; kanıt yoksa UNKNOWN
  "subject": "Matematik|Türkçe|Fen|İngilizce|Sosyal Bilgiler|Din Kültürü",
  "topic": "string|null",
  "learning_outcome": "string|null",
  "skill": "string|null",
  "level": 1,                                     // 1–4
  "confidence": 0.0,                              // 0..1
  "evidence": "string|null",                      // teşhise dayanak
  "intervention": { "kind": "concept_repair|practice|strategy|time_control",
                    "steps": ["..."] },
  "video_needed": false,
  "reinforcement_question_count": 0,              // 0..3
  "needs_human_review": true                      // confidence düşükse true
}
```

Kurallar:

1. `confidence` 0..1 dışına çıkamaz; düşük güvende `needs_human_review` **true** olur.
2. `error_type` yalnızca yedi kod + `UNKNOWN` olabilir; serbest metin olarak sızamaz.
3. `level` 1–4 aralığında; `reinforcement_question_count` makul üst sınırla.
4. Müfredat eşlemesi **kanıt bağlantısı olmadan** `VERIFIED` sayılamaz (bkz. `lgs-question-engine`).
5. Zorunlu alanlar eksikse yanıt reddedilir; eksik alan "uydurularak" doldurulmaz.

## Halüsinasyon / kaynak uydurma önleme

- AI **var olmayan MEB kaynağı, URL, kitapçık veya cevap anahtarı uyduramaz**.
- AI üretimi içerik asla resmî MEB içeriği gibi etiketlenemez (`AI_GENERATED` ayrımı korunur).
- AI, provenance veya verification alanlarını **dolduramaz**; yalnızca aday üretir, insan onaylar.
- Prompt içinde öğrenci adı/okul/kimlik gibi gereksiz kimlikler gönderilmez (veri minimizasyonu).
- Provider/model kimliği yanıtta açıkça döner (`provider`, `model`) — hatanın kaynağı izlenebilir olmalı.

## Hata temizliği ve sınırlamalar

- Upstream hata mesajları istemciye olduğu gibi akmaz; `providers.ts` gövdeyi 300 karaktere
  kısaltır. Yeni hata yolları da aynı disiplini korumalı.
- `/api/ai` girişleri sınırlıdır: prompt karakteri (`AI_MAX_PROMPT_CHARS`), görsel boyutu
  (`AI_MAX_IMAGE_BYTES`), gövde JSON parse kontrolü. Yeni alan eklerken de sınır koy.
- Sağlayıcı başarısızlığında `attempts[]` her denemenin sağlayıcısını/reason'unu taşır; bu
  teşhis zinciri kaybettirilmemelidir.

## Bu görevde kontrol

```sh
npm run test:ai          # 19 sözleşme/fallback testi (stub tabanlı)
npx tsc --noEmit
```

Ayrıntılı sağlayıcı kuralları için `ai-provider` skill'ini kullan.
