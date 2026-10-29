# AI'sız Fizibilite Araştırması — GitHub / Reddit / Akademik Kaynaklar

> Tarih: 2026-10-27 · Kapsam: LGS uygulamasının AI gerektiren 4 özelliğinin AI'sız/ücretsiz uygulanabilirliği.
> İşaretler: ✅ = tamamen AI'sız (kural/şablon) · 🔶 = ücretsiz yerel küçük model gerektirir · ❌ = AI'sız gerçekçi değil

## 1) Sesli Anlatımın Tarayıcıda Metne Çevrilmesi

### Web Speech API (SpeechRecognition)
- Chrome/Edge `webkitSpeechRecognition`, `lang='tr-TR'` destekli; Chrome sesi Google sunucularına gönderir → **internet şart, çevrimdışı çalışmaz** (MDN: https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition). Firefox'ta varsayılan **kapalı** (`dom.webspeech.recognition.enable`; https://wiki.mozilla.org/Web_Speech_API_-_Speech_Recognition). Safari daha kısıtlı.
- Chrome **cihaz üstü (on-device)** tanıma üzerinde çalışıyor (`processLocally`, SODA backend; https://github.com/WebAudio/web-speech-api/blob/main/explainers/on-device-speech-recognition.md — tr-TR listede). Henüz standart değil.
- Doğruluk değişken; kesintisiz akış için yaygın desen: `recognition.onend = () => recognition.start()` döngüsü + `interimResults=true` (https://blog.addpipe.com/a-deep-dive-into-the-web-speech-api/, https://webreflection.medium.com/taming-the-web-speech-api-ef64f5a245e1).

### Sessizlikte MediaRecorder'ın Durmaması (tamamen kural tabanlı ✅)
- RecordRTC issue #630 — RMS eşiği + debounce: https://github.com/muaz-khan/RecordRTC/issues/630
- `AnalyserNode` + `minDecibels` + rAF: https://stackoverflow.com/questions/71103807/detect-silence-in-audio-recording
- `detectSilence()` örneği: https://stackoverflow.com/questions/46543341/how-can-i-extract-the-preceding-audio-from-microphone-as-a-buffer-when-silence
- RMS ≈ 0.01 + 3 sn eşiği: https://pavi2410.com/blog/detect-silence-using-web-audio/
- Üretim kalitesinde durum makinesi: https://cdn.jsdelivr.net/npm/@stream-io/video-client@1.55.2/src/helpers/no-audio-detector.ts
- Tarayıcı bug'ı (sessiz track'te boş Blob, crbug/1223382) workaround: https://stackoverflow.com/questions/68620750/getting-empty-blob-from-mediarecorder-when-web-audio-api-is-silent

### Çevrimdışı seçenekler (🔶)
- **vosk-browser** (WASM Vosk, WebWorker): https://github.com/ennuicastr/vosk-browser (bakımlı fork: https://github.com/lichess-org/vosk-browser) + **vosk-model-small-tr-0.3** (35 MB, Apache 2.0; https://alphacephei.com/vosk/models — resmi WER "TBD", kalite sınırlı olabilir).
- **whisper.cpp WASM**: https://ggml.ai/whisper.cpp/ ; **transformers.js Whisper** (WebGPU): https://github.com/huggingface/transformers.js — Türkçe küçük modeller zayıf (tiny WER ~0.53: https://www.mdpi.com/2079-9292/13/21/4227); ince ayarlı `whisper-small-tr` WER 7.75% (https://huggingface.co/emredeveloper/whisper-small-tr) ama tarayıcıda yüzlerce MB + yavaş.
- Hibrit desen: canlı önizleme Web Speech, kalıcı transkripsiyon sunucuda küçük Whisper/Vosk: https://dev.to/linmingren/building-a-browser-based-speech-to-text-system-with-whisper-ai-23e5

**Karar:** Kayıt + sessizlik kesme ✅ kural tabanlı. Transkripsiyon sıfır-AI değil: Web Speech (Google sunucusu, internet şart) veya 🔶 yerel Vosk/Whisper. Öneri: Web Speech birincil + RMS sessizlik; çevrimdışı Vosk-tr fallback.

## 2) El Yazısı Çözüm Fotoğrafı Analizi

### OCR
- **tesseract.js** (https://github.com/naptha/tesseract.js, `tur.traineddata` var) ama el yazısında bilinçli zayıf (https://joseurena.medium.com/tesseract-ocr-evaluating-handwritten-text-recognition-1c6db85b2e7f; Reddit 2025 incelemesi: https://www.reddit.com/r/computervision/comments/1mbpab3/updated_2025_review_my_notes_on_the_best_ocr_for/ — messy el yazısında ~%48). Matematik + Türkçe + el yazısı en kötü senaryo.
- Formül tanıma 🔶: **Pix2Text** (https://github.com/breezedeus/Pix2Text), **pix2tex/LaTeX-OCR** (https://github.com/lukas-blecher/LaTeX-OCR), Math2LaTeX (https://github.com/wz-ml/Math2LaTeX). CROHME akademik sınırı bile ~%45 ExpRate (https://github.com/fisherman611/handwritten-mathematical-expression-recognition).

### GitHub "matematik ödev kontrol" projeleri
- Hepsi AI'lı: ForMath (Tesseract.js + GPT-4 + Wolfram: https://github.com/darthvader58/biryani), SmartSolve (Tesseract.js + Gemini: https://github.com/larrikin-coder/SmartSolve). **AI'sız tam otomatik çözüm kontrolü projesi bulunamadı.**

### Kural tabanlı cevap kontrolü (✅, OCR'dan bağımsız)
- SymPy `grade_answer` (https://cobi-inc.github.io/pita/utils/grading_utils/math/math_grader/), **pie-framework/math-validation** (https://github.com/pie-framework/math-validation), **nerdamer** (https://github.com/jiggzson/nerdamer), Khan KAS "Spotter" tekniği (http://lightandmatter.com/spotter/article.pdf), **google/mathsteps** (https://github.com/google/mathsteps).

**Karar:** Tam otomatik foto→hata sınıflandırma ❌. Gerçekçi ✅ yaklaşım: fotoğraf = kanıt, öğrenci sonucu ayrıca dijital girer, CAS ile kontrol edilir. Adım fotoğrafı isteğe bağlı "öğretmen incelemesi" kalır.

## 3) Türkçe LGS/MEB YouTube Video Katalogları

- **Hazır halka açık katalog/dataset yok.** EBA katalog API'si yok; GitHub EBA scriptleri eski (https://github.com/denizemekli/Eba-Canli-Ders, https://github.com/Andromeda606/eba-tools). Resmi içerik: MEBİ (https://mebi.eba.gov.tr), müfredat ağacı: https://mufredat.meb.gov.tr.
- Kanal/playlist hammaddesi: Hocalara Geldik 8. Sınıf (~1.700 video), Benim Hocam, Tonguç (https://br.youtubers.me/turkey/education/top-500-education-channels-dentro-turkey).
- **YouTube Data API v3** (https://developers.google.com/youtube/v3) ile katalog BİR KEZ kurulup statik JSON'da tutulmalı; çalışma anında arama yapılmamalı (deterministik değil, linkler 20-60 günde çürüyor: https://arxiv.org/pdf/2506.11727v3).
- Öneri mekanizması ✅: kazanım kodu ↔ video eşleme tablosu; sorunun kazanımı → o etiketteki videoları sırala.

**Karar: ✅ AI'sız yapılabilir (en güçlü adaylardan).** Tek iş: elle kürasyon (kazanım → video URL JSON) + API ile metadata bakımı.

## 4) Kural/Şablon Tabanlı Soru Üretimi (LLM'siz)

- **mathgenerator** (100+ üretici, MIT; https://github.com/lukew3/mathgenerator — bakım uyarısı, fork mantıklı), **RandMatQuGeA** (TypeScript, 125+ konu, cevap anahtarı hesaplanır: https://github.com/richie-rich90454/RandMatQuGeA), **MathMaster-Adaptive-Math-Quiz** (https://github.com/rashidrupani/MathMaster-Adaptive-Math-Quiz), januschung/math-worksheet-generator (https://github.com/topics/maths).
- Akademik kanıt: "Procedural generation of problems for elementary math education" (IJSG 2021, https://doi.org/10.17083/ijsg.v8i2.396) — 5 parametreli şablon + **kural tabanlı yanlış seçenek üretimi**, uzman onayı, %56 zaman tasarrufu. TemplateMath/TemplateGSM (ICLR 2025, https://github.com/iiis-ai/TemplateMath).

**Karar: ✅ en olgun alan.** Her LGS kazanımı için parametreli şablon + kural tabanlı distractor; cevap anahtarı formülle otomatik, CAS ile doğrulanır; Türkçe şablonlar elle yazılır. **Sınır:** uzun metin/okuma-anlama ("yeni nesil") soruları şablonla üretilemez — üretim sayısal/prosedürel konularla sınırlı.

## Özet Tablo

| Özellik | AI'sız? | En iyi pratik yol |
|---|---|---|
| 1. Ses transkripsiyonu | Kısmen ✅ (kayıt/sessizlik) + Web Speech (sunucu AI'sı) / 🔶 Vosk-tr | Web Speech birincil + RMS sessizlik; 🔶 Vosk-tr fallback |
| 2. El yazısı foto analizi | ❌ tam otomatik; ✅ "foto = kanıt + dijital cevap + CAS kontrolü" | SymPy/nerdamer/math-validation; OCR'a güvenme |
| 3. YouTube video katalogu | ✅ | Elle küratörlü kazanım→video JSON + YouTube Data API bakımı |
| 4. Soru üretimi | ✅ | mathgenerator/RandMatQuGeA desenleri + IJSG şablon+distractor; Türkçe şablonlar elle |

Uyarılar: (a) Web Speech Firefox'ta yok ve veriyi Google'a gönderir; (b) Vosk tr küçük modelinin WER skoru yok — önce test; (c) hazır LGS video dataset'i yok — kürasyon bize düşer; (d) mathgenerator bakımsız olabilir.