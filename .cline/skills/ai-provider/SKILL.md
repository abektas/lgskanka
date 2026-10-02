---
name: ai-provider
description: Nüli (LGS AI Coach) AI sağlayıcı katmanı işleri için proje-özgü kurallar. OpenAI → Gemini → OpenRouter fallback zinciri, sağlayıcı seçimi ve sırası, model keşfi, zaman aşımı ve hata sözleşmesi, metin/görsel giriş sınırları, env değişkenleri ve anahtar güvenliği değişikliklerinde kullan.
---

# ai-provider

Sağlayıcı katmanı tek dosyada toplanır: **`app/api/ai/providers.ts`**.
HTTP sınırı: **`app/api/ai/route.ts`**. UI: `components/study-flow.tsx`.

## Yetkili kaynak

**`AGENTS.md` → "AI providers and secret handling"**.

## Mimari (bugün)

- Zincir: **OpenAI → Gemini → OpenRouter** (`PROVIDER_ORDER`).
- `AI_PROVIDER` birincili seçer; `AI_FALLBACK_ORDER` sırayı tamamen değiştirir.
- Anahtarı/URL'i tanımlı olmayan sağlayıcı zincire **hiç girmez** (`isConfigured`).
- Bir sağlayıcı hata verirse sıradakine geçilir; hepsi düşerse `AllProvidersFailed`
  (HTTP 502) ve her denemenin `provider/status/error` bilgisi `attempts[]` içinde döner.
- `ProviderError.status` upstream HTTP kodudur; ağ hatasında `0`.
- Zaman aşımı `AI_TIMEOUT_MS` (varsayılan 45 s), `AbortSignal.timeout` ile uygulanır.
- `OPENAI_MODEL` verilmemişse OpenAI için `/models` üzerinden model keşfi yapılır ve
  süreç ömrü boyunca önbelleklenir.

## Env sözleşmesi

`AI_PROVIDER`, `AI_FALLBACK_ORDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`,
`GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_BASE_URL`, `OPENROUTER_API_KEY`,
`OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`, `AI_TIMEOUT_MS`, `AI_MAX_PROMPT_CHARS`,
`AI_MAX_IMAGE_BYTES`, `AI_APP_URL`.

- Bu liste `.env.example` ile senkron olmalıdır; yeni değişken ekleniyorsa örnek dosya da güncellenir.
- `.env.local` git'e girmez; `.env.example` **yalnızca yer tutucu** içerir.
- Kod, diff, log, ekran görüntüsü ve dokümana anahtar **yazılmaz**; gerekirse yalnızca
  "tanımlı mı / değil" bilgisi raporlanır.

## Giriş sınırları ve hata disiplini

- Prompt uzunluğu `AI_MAX_PROMPT_CHARS`, görsel `AI_MAX_IMAGE_BYTES` ile sınırlıdır; aşım
  413/400 döner ve sağlayıcıya istek gitmez.
- Upstream hata gövdesi istemciye ham iletilmez; 300 karaktere kısaltılır.
- `imageData` `data:` URL veya ham base64 olabilir; ayrıştırma `parseImageData` içinde yapılır.
- JSON parse hatası 400, gövdesiz/bozuk istek 400 döner; stack trace istemciye sızmaz.

## Test gerçeği

`npm run test:ai` gerçek kimlik doğrulama **değildir**: sahte (stub) sunucular kullanır ve
yalnızca zincir sırası, istek şekli ve hata mesajlarını doğrular. Canlı sağlayıcı
sağlığı bu testle gösterilmez; ayrıca uçtan uca doğrulama gerekir.

## Karar bekleyen konu

Yerel (`local`) sağlayıcı kaldırıldı; `README.md` ve `AGENTS.md` hâlâ ondan söz ediyor.
Mimari değişiklik onaylanmadan ne yeni sağlayıcı eklenmeli ne de mevcut zincir
değiştirilmelidir. Önce Product Owner kararı alınır.

AI çıktısının doğrulanabilirliği için: `ai-learning-engine`.
Öğrenci verisi kuralları için: `child-privacy-kvkk`.
