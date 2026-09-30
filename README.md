# LGS AI Coach UI v2

Premium AI Tutor + gamified student experience.

## Included
- Premium dashboard
- Gender/avatar selection with localStorage profile
- Daily tasks and XP
- Working question flow
- Answer evaluation demo
- H1-H7-oriented first-error analysis UI
- Student reason selection
- Voice explanation / solution photo entry points
- Privacy messaging for temporary analysis files
- AI Coach screen
- Progress and error taxonomy screen
- Rewards / game center
- Responsive mobile layout

## Run

```bash
npm install
npm run dev
```

Then open `http://localhost:3000`.

## AI sağlayıcısı (`/api/ai`)

Tek bir env değişkeniyle sağlayıcı seçilir; sıradaki sağlayıcı otomatik denenir.

```bash
AI_PROVIDER=auto              # auto | gemini | openrouter | local
# Varsayılan yedek sırası: gemini -> openrouter -> local
# AI_FALLBACK_ORDER=gemini,openrouter,local   (sırayı tamamen değiştirir)

GEMINI_API_KEY=               # https://aistudio.google.com/apikey
OPENROUTER_API_KEY=           # https://openrouter.ai/keys
LOCAL_AI_BASE_URL=            # LM Studio/Ollama: http://localhost:1234/v1
```

- Ayarı (anahtar/URL) olmayan sağlayıcı zincire hiç girmez.
- Hepsi düşerse `502` + her denemenin sebebini listeleyen Türkçe hata döner.
- Yanıt sözleşmesi: `{ answer, provider, model }`.

Sağlayıcı katmanı testi (ağa çıkmaz, taklit sunucular kullanır):

```bash
npm run test:ai
```

## Next integration
1. Replace demo question state with `/api/questions`.
2. Connect answer submission to the AI analysis endpoint.
3. Persist only derived learning data; do not persist raw voice/photo inputs after analysis.
4. Add verified question-bank records and server-side answer keys.
5. Connect Supabase/PostgreSQL.
