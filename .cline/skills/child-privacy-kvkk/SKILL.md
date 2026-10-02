---
name: child-privacy-kvkk
description: Nüli (LGS AI Coach) çocuk/öğrenci veri gizliliği ve KVKK işleri için proje-özgü kurallar. Profil verisi, ses kaydı, çözüm fotoğrafı, transcript, dış AI sağlayıcıya veri aktarımı, loglama, saklama/silme, kimlik doğrulama, yetkilendirme ve rate limit değişikliklerinde kullan.
---

# child-privacy-kvkk

Kullanıcılar **8. sınıf öğrencileridir**: veri minimizasyonu ve saklama kuralları daha da
sıkı uygulanır. Yasal uygunluk yalnızca bu teknik kontrollerle sağlanmış sayılmaz
(nitelendirici değil, hukuki değerlendirme gerektirir).

## Yetkili kaynak

**`AGENTS.md` → "Privacy, student safety, and KVKK"** ve **"Security"**.

## Bugünkü gerçek durum (varsayım değil, kod)

| Konu | Durum | Nerede |
|---|---|---|
| Profil tercihi | Tarayıcıda `localStorage` (ad değil, yalnızca avatar/tercih) | `components/profile-provider.tsx` |
| Ses kaydı | `MediaRecorder` ile geçici; analiz sonrası bileşen state'inden temizlenir | `components/voice-recorder.tsx`, `components/study-flow.tsx` |
| Çözüm fotoğrafı | Geçici `imageData`; analiz sonrası state'ten temizlenir | `components/study-flow.tsx` |
| Sunucu kalıcılığı | **Yok** — veritabanı/oturum/hesap yok | `db/001_question_bank.sql` uygulanmamış |
| Yetkilendirme / rate limit | **Yok** (`/api/ai`, `/api/questions`, `/api/games/runner` açık) | `app/api/*/route.ts` |
| Dış aktarım | Soru metni, öğrenci cevabı, işaretlenen zorluk, transcript ve isteğe bağlı görsel sağlayıcıya gider | `app/api/ai/route.ts` → `providers.ts` |

## Kurallar

1. **Veri minimizasyonu**: öğrencinin adı, okulu, sınıf numarası, cihaz/ses kimliği gerekmiyorsa
   toplanmaz ve gönderilmez.
2. **Ham medya kalıcı değildir**: ses ve fotoğraf yalnızca analiz girdisidir; başarı **ve** hata
   yolunda temizlenir. Hata ayıklama için istisna tutulacaksa ayrıca onay gerekir.
3. **Transkript** de öğrenci içeriğidir: saklama süresi ve amaç açıklanır.
4. **UI ile gerçek davranış eşleşmelidir**: "kalıcı olarak silindi" ifadesi ancak backend'de de
   kalıcı veri yoksa doğrudur. Aksi halde metin düzeltilir.
5. **Dış aktarım şeffaftır**: hangi verinin hangi sağlayıcıya gittiği ve işleme amacı
   yaş uygun dille açıklanmalı.
6. **Loglama**: kimlik, medya, transcript veya ham prompt **loglara yazılmaz**.
7. **Yetkilendirme/izin**: hesap, veli onayı ve silme talebi akışı üretime geçmeden önce
   tanımlanmalı; API'de yetki kontrolü gizli UI'a bırakılamaz.
8. **Rate limit/abuse koruması**: her yazma yapan rotada sınır olmalı; XP/ödül manipülasyonu
   istemci tarafında kazanç üretmemeli.
9. **Secret'lar**: API anahtarları yalnızca `.env.local`/managed store'da; kod, diff, log,
   ekran görüntüsü, dokümana girmez. `.env.example` yalnızca yer tutucu içerir.
10. **Kişisel veri Git'e girmez**: fixture, test verisi veya loglarda öğrenci PII'si bulunmaz.

## Yeni veri toplayan her değişiklikte sorulacak sorular

- Bu veri olmadan özellik çalışır mı? → çalışıyorsa **toplanmaz**.
- Saklama süresi ve silme yolu tanımlı mı?
- Kim erişebilir, hangi rollere bağlı?
- Dış servise gidiyor mu, gerekçesi ve temizleme davranışı ne?
- Onay/riza metni hangi dosyada?

Denetim: `security-reviewer` ajanı. Uygulama özeti AGENTS.md'de tanımlıdır.
