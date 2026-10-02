---
name: lgs-education-engine
description: Nüli (LGS AI Coach) pedagoji ve öğrenme motoru işleri için proje-özgü kurallar. H1–H7 ilk-hata taksonomisi, seviye 1–4, mastery, adaptive haftalık test, spaced repetition, 5 haftalık deneme takvimi, koçluk metni ve öğrenci ilerlemesi görünürlüğü değişikliklerinde kullan.
---

# lgs-education-engine

LGS eğitim/pedagoji katmanı: öğrenciye verilen her teşhis ve plan bu kurallara tabidir.

## Yetkili kaynak

**`AGENTS.md` → "Error taxonomy: H1–H7"** ve **"Learning loop and assessment"** bölümleri
(primary/authoritative). Bu skill, kodu okumak ve çalışma komutlarını bilmek içindir;
**anlam tanımını yetkili kaynaktan tekrar yazmaz.**

## ✅ Çözüldü: H1–H7 canonical sözlüğü (2026-10-01)

H1–H7 anlam çelişkisi **kapandı**. `AGENTS.md`, `LGS_AI_COACH_MASTER_PROJE_PLANI_v2.0.md` §6
ve runtime kodu (`data/content.ts` `errorTypes`, `app/api/ai/route.ts` `buildPrompt`) artık
**aynı canonical sözlüğü** kullanır:

| Kod | Canonical anlam |
|---|---|
| H1 | Kavramsal / bilgi eksikliği |
| H2 | Yöntem / strateji eksikliği |
| H3 | Okuma / anlama / modelleme |
| H4 | Hesaplama / işlem hatası |
| H5 | Gereksiz bilgiyi ayıklayamama |
| H6 | Bilgileri ilişkilendirememe |
| H7 | Dikkat / acele / rastgelelik |

Kurallar:
1. Yeni kod/yüzey eklerken **bu** sözlük esas alınır; yeni bir yüzeyde eski jenerik
   anlamlar (H2 = misconception, H4 = strategy, H5 = procedure, H6 = attention,
   H7 = time/exam management) **geri getirilmez**.
2. H7 = dikkat/acele/rastgelelik; **time/exam management ayrı bir kod değildir** ve H7
   yeniden yorumlanarak kullanılmaz.
3. Bir kodun anlamını değiştirmek Product Owner kararıdır: Master Plan §6, `AGENTS.md`,
   `data/content.ts` ve AI prompt **aynı değişiklikte** bilinçli güncellenir; sessiz
   yeniden yorum yapılmaz.
4. Mevcut öğrenciye gösterilmiş geçmiş veri (paylaşımlar, rozetler) etiket değişiminde
   dikkate alınır; sessizce yeniden yorumlanmaz.

## Temel pedagoji kuralı

- Yanlış cevap otomatik olarak **konu eksikliği** değildir. Teşhis **ilk hata noktasına** (first error) göre yapılır; kanıt yetersizse "belirsiz" denir ve zorlanmış etiket verilmez.
- Hata etiketi öğrencinin sabit bir yeteneğini değil, **öğrenilebilir bir beceri açığını** gösterir.
- Dil: destekleyici, açık, yaş uygun, utandırmayan.
- Tek bir yanıt, öğrenci hakkında kalıcı yargı temeli oluşturmaz.
- Mastery/takvim önerisi **gerçek öğrenci ilerlemesine** dayanmalıdır; demo veri ise demo olarak etiketlenmelidir.

## Kavram haritası

| Kavram | Nerede |
|---|---|
| H1–H7 tanım/tip + UI metni | `data/content.ts` (`errorTypes`, `ErrorType`) |
| AI teşhis istemi (H eşlemesi) | `app/api/ai/route.ts` (`buildPrompt`) |
| Seviye/ilerleme/arayüz metinleri | `data/content.ts` (`subjects`, `examPlan`, `weeklyProgress`, `tasks`) |
| Çalışma akışı ve öğrenci girişi | `components/study-flow.tsx`, `app/calis/page.tsx` |
| Hata analizi ekranı | `app/ilerleme/page.tsx` |

## Planlama motoru kuralları (mastery, adaptive, spaced repetition)

- **Mastery**: tek bir yanlttan değil, kazanım bazlı tekrar eden kanıttan hesaplanır; eşikler heuristic'tir ve "kesin bilimsel" diye sunulmaz.
- **Adaptive seçim**: müfredat kapsamı + öğrenci performansı + zorluk dengesi; **açıklanabilir ve denetlenebilir** olmalı (AGENTS.md gereği).
- **Spaced repetition**: kanıtlanmış mastery + yakınlık + hata tipine göre; yanlış teşhis düzeltme/dismiss yolu bulunmalı.
- **Haftalık test ve 5 haftalık deneme**: LGS yapısına/yayın saatlerine yakın olmalı; **üretilen deneme resmî sınav gibi sunulamaz**.
- Bu motorların hiçbiri bugün kalıcı olarak uygulanmış değildir (öğrenci ilerlemesi `localStorage`'da); yeni kod yazarken mevcut demo akışı bozulmamalı.

## Bu görevde kontrol

```sh
npx tsc --noEmit && npm run build     # tip + derleme
npm run test:ai                       # provider sözleşmesi (stub tabanlı)
```

Pedagoji denetimi `education-reviewer` ajanıyla, diff denetimi `lgs-reviewer` ile yapılır.
