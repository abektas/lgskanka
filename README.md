# LGS AI Coach

8. sınıf öğrencileri için yapay zekâ destekli LGS sınav hazırlık uygulaması.

## Özellikler

- 6 ders: Matematik, Fen Bilimleri, Türkçe, İnkılap Tarihi, Din Kültürü, İngilizce
- 2018–2026 resmî LGS soru bankası (provenance-preserved)
- AI destekli soru analizi (pedagojik kazanım, zorluk, beceri)
- Gamifikasi: XP, rozetler, günlük görevler
- Premium dashboard ve ilerleme takibi
- Sesli açıklama ve çözüm fotoğrafı giriş noktaları

## Teknoloji

- **Framework:** Next.js 16 + React 19
- **Deployment:** Cloudflare Pages
- **AI:** OpenAI / Gemini / OpenRouter / Ollama (yerel)
- **Build:** Standalone output

## Kurulum

```bash
npm install
npm run dev
```

## Ortam Değişkenleri

`.env.example` dosyasını `.env.local` olarak kopyalayın:

```bash
cp .env.example .env.local
```

| Değişken | Açıklama |
|----------|----------|
| `AI_PROVIDER` | `auto`, `gemini`, `openrouter`, `openai`, `local` |
| `GEMINI_API_KEY` | Google AI Studio anahtarı |
| `OPENROUTER_API_KEY` | OpenRouter anahtarı |
| `OPENAI_API_KEY` | OpenAI anahtarı |
| `LOCAL_AI_BASE_URL` | Yerel AI sunucusu URL (örn. `http://localhost:11434/v1`) |

## Testler

```bash
npm run test:ai          # AI sağlayıcı testi
npm run test:source      # Kaynak ingestion testi
npm run test:taxonomy    # Taksonomi testi
```

## Dağıtım

### Cloudflare Pages

```bash
npm run build
wrangler pages deploy
```

### GitHub

```bash
git remote add origin <repo-url>
git push -u origin main
```

## Lisans

[MIT](LICENSE)
