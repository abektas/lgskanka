# Session Handoff — 2026-10-23 (güncel)

## Active Tasks
- Yok — LGS 2015 tam çıkarma TAMAMLANDI (90/90). Sıradaki adım onay bekliyor.

## Yapılanlar (bugün)
- `scripts/source-ingestion/extract_2015_v3.py` nihai sürüme getirildi: görünmez çizim düzeltmesi (ink_shrink), piksel düzeyi 20pt trim, sütun ayıracı sınırı, en yakın soruya bağlama (D şeritleri), `cmax` birim hatası düzeltmesi (gri tablo sorusu 43pt'ye sıkışmıştı → 520pt).
- 90 soru kırpıldı → `lgs_18_26/{turkce,matematik,fen-bilimleri}/` 20'şer; `inkilap-tarihi,din-kulturu,ingilizce/` 10'ar.
- Her klasörde: PNG + `manifest_2015.json` + `answers_2015.json` + `analysis_2015.jsonl` (analysisStatus: PENDING).
- `public/exams/2015-*.png` kopyaları (90) hazır.
- Denetim: 306/360 kenar tam 20pt; kalanlar fiziksel istisna (sütun ayıracı yanı 5-13pt, Q1 üst dekor şeridi, son soru alt çizgisi — soru metni kesik değil).
- Skill `lgs-pdf-crop-extraction`'a 2015 dersleri eklendi.

## Devreden kararlar (kalıcı)
- **Tek işçi**: SHARDS=1 (30GB RAM, OOM önleme).
- **Metin-öncelikli hibrit analiz**: TU2'de kanıtlandı (547 soru, %100 cevap). Yerel VLM Türkçe metni pikselden okuyamaz.
- **Gösterim = PNG crop**: dots-ocr yalnız analiz verisi (questionText) için; altı-çizili sorular `underlineDependent:true`.
- **Kural tabanlı H1-H7 sınıflandırma**: Kullanıcı AI değerlendirme reddetti; kural tabanlı hata tespiti yapılacak.
- **Supabase** kullanıcı verisi için (localStorage değil); çevrimdışı model tercihi.
- **Kanıt görselleri sohbete gömülmez** — kullanıcı yalnız klasör yolu ile inceler (token tasarrufu).
- **Token kotası**: 15M/gün Evren, 03:00 reset. Bugün 03:00'ten beri ~1,5M (optimizasyonlar çalışıyor: Hermes sıkıştırma + prompt kapakları + oturum disiplini).

## Dosyalar
- `scripts/source-ingestion/extract_2015_v3.py` — 2015 çıkarıcı (nihai)
- `lgs_18_26/*/manifest_2015.json|answers_2015.json|analysis_2015.jsonl` — 2015 çıktıları
- `app/api/ai/route.ts`, `scripts/analyze_lgs18_26.py`, `scripts/source-ingestion/analyze_text_mode.py`, `scripts/source-ingestion/analyze_lgs18_26_text.py` — token kapakları

## Blockers
- Yok (Supabase kurulumu ve H1-H7 sınıflandırıcı sıradaki işler).

## Next Steps
1. Kullanıcıdan analiz adımı onayı: `analysis_2015.jsonl` talimatname analizi (kural tabanlı, tek işçi).
2. Kural tabanlı H1-H7 sınıflandırıcı (AI'sız).
3. Supabase kurulumu.
4. LGS 18-26 analizi tamam (810/810, servis disabled) — gerekirse yeniden başlatma `systemctl --user start lgs18-26-analysis.service`.