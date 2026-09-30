# LGS AI COACH — MASTER PROJE PLANI v2.0

> Bu belge; mevcut prototip, daha önce belirlenen eğitim kuralları, teknik kararlar, gizlilik ilkeleri, UI/gamification hedefleri ve üretim yol haritasını tek bir master dokümanda toplar.
>
> **Amaç:** Bu dosya proje geliştirilirken ana referans/roadmap olarak kullanılacaktır.

---

# 1. PROJE TANIMI

**LGS AI COACH**, 8. sınıf öğrencisinin LGS hazırlığını kişiselleştiren bir AI eğitim platformudur.

Temel amaçları:

- Öğrencinin soru çözmesini sağlamak.
- Yanlış cevabın yalnızca sonucunu değil, **ilk hata noktasını** bulmak.
- Hata türünü H1–H7 modeliyle sınıflandırmak.
- Konu, kazanım ve beceri alanını belirlemek.
- Kişiselleştirilmiş konu tekrarı yapmak.
- MEB/doğrulanmış kaynaklar ve uygun YouTube içerikleri önermek.
- Pekiştirme soruları üretmek.
- Öğrenmeyi mini test/retest ile doğrulamak.
- Öğrencinin mastery durumunu takip etmek.
- Haftalık adaptif testler hazırlamak.
- Her 5 haftada LGS benzeri özgün deneme uygulamak.
- AI öğretmen ve AI koç olarak çalışmak.
- Gerçek ilerlemeye dayalı motivasyon sağlamak.
- XP, rozet, oyun ve karakter gelişimi ile öğrenme davranışını desteklemek.

---

# 2. ANA ÜRÜN FELSEFESİ

Sistem yalnızca:

> Soru sor → cevap al

uygulaması değildir.

Ana öğrenme döngüsü:

```text
ÖĞRENCİ
   ↓
SORU ÇÖZER
   ↓
CEVAP
   ↓
BAŞARI / HATA ANALİZİ
   ↓
İLK HATA NOKTASI
   ↓
KONU + KAZANIM + BECERİ
   ↓
KİŞİSEL MÜDAHALE
   ↓
TEKRAR
   ↓
PEKİŞTİRME
   ↓
RETEST
   ↓
MASTERY
   ↓
ADAPTİF PLAN
   ↓
YENİ SORU
```

Öğrenci arayüzünün temel sorusu:

**“Şimdi ne yapmalıyım?”**

---

# 3. EĞİTİM KAPSAMI

## 3.1 Kaynak önceliği

Kullanılacak kaynaklar:

1. MEB öğretim programı/kazanımları.
2. 2018 ve sonrası gerçek LGS soruları.
3. MEB örnek soruları.
4. MEB 8. sınıf resmi materyalleri.
5. Doğrulanmış yardımcı kaynaklar.
6. Doğrulanmış eğitim videoları.
7. AI tarafından üretilen özgün içerik.
8. Öğrenci performansına göre kişiselleştirilmiş AI soruları.

## 3.2 Kesin dışlama

Normal LGS soru havuzundan:

- TEOG.
- 2018 öncesi merkezi sınav soruları.
- Gerçek LGS sorularının AI tarafından kopyalanmış versiyonları.
- Kaynağı doğrulanmamış soruların gerçek LGS olarak sunulması.

çıkarılır.

> Not: 2018–2026 dönemi mevcut LGS merkezi sınav geçmişidir. “Son 15 yıl” ifadesi doğrudan LGS merkezi sınavları açısından mümkün değildir; bu nedenle normal LGS sistemi 2018+ esasına göre çalışır.

---

# 4. SEVİYE SİSTEMİ

## Seviye 1 — Temel

- Temel kavramlar.
- Ön koşul bilgiler.
- Kısa/doğrudan sorular.
- Kontrollü uygulama.

## Seviye 2 — Gelişen

- 7. sınıf bilgi pekiştirme.
- 8. sınıfa geçiş.
- Orta zorluk.
- Yeni nesil sorulara geçiş.

## Seviye 3 — LGS Hazırlık

- 8. sınıf müfredatı.
- LGS becerileri.
- Yorumlama.
- Çıkarım.
- Grafik/tablo.
- Çoklu bilgi.
- Problem çözme.
- Analiz.

## Seviye 4 — İleri LGS

- Çok adımlı sorular.
- Çoklu bilgi.
- Bilgi transferi.
- Üst düzey muhakeme.
- Zor yeni nesil sorular.
- Zaman yönetimi.

### Önemli tasarım kararı

Öğrenci seviyesi ile soru zorluğu **ayrı alanlar** olmalıdır.

Örnek:

```text
student_level = 2
question_difficulty = 3
```

---

# 5. SEVİYE BELİRLEME

Varsayılan başlangıç:

**Seviye 1**

Ancak öğrenci başlangıçta Seviye 2/3/4 seçebilir.

İleri seviyeden başlayan öğrencide kısa seviye belirleme testi:

- 12–20 soru.
- Temel bilgi.
- Uygulama.
- Yorumlama.
- Yeni nesil.
- Çok adımlı soru.

Sistem:

- Öğrencinin seçtiği seviyeyi başlangıç tercihi olarak kabul eder.
- Gerçek performansı ayrıca ölçer.
- Öğrenciyi zorunlu biçimde otomatik aşağı/yukarı taşımaz.
- Seviye geçiş testi önerir.
- Öğrenci tercihi + gerçek performansı birlikte kullanır.

---

# 6. HATA ANALİZ MODELİ H1–H7

## H1 — Kavramsal eksiklik

Öğrenci temel kavramı bilmiyor veya yanlış biliyor.

## H2 — Yöntem / strateji eksikliği

Kavramı biliyor fakat çözüm yaklaşımını kuramıyor.

## H3 — Okuma / anlama / modelleme

Sorudaki bilgiyi doğru okuyamıyor veya matematiksel/akademik modele dönüştüremiyor.

## H4 — Hesaplama / işlem hatası

Doğru yöntemi seçmesine rağmen işlem sırasında hata yapıyor.

## H5 — Gereksiz bilgiyi filtreleyememe

Verilen bilgilerden hangilerinin gerekli olduğunu ayırt edemiyor.

## H6 — Bilgileri ilişkilendirememe

Birden fazla bilgi parçasını birlikte kullanamıyor.

## H7 — Dikkat / acele / rastgelelik

Kavram ve yöntem yeterli olmasına rağmen dikkatsizlik/acele nedeniyle hata yapıyor.

### Ana kural

**Yanlış cevap = otomatik H1 değildir.**

AI önce ilk hata noktasını belirlemelidir.

---

# 7. ÖĞRENCİ SORU AKIŞI

## Doğru

```text
Doğru
 ↓
Cevap kaydı
 ↓
XP
 ↓
Mastery güncelle
 ↓
Sonraki soru
```

## Yanlış

Öğrenciye:

- Soruyu anlamadım.
- Yöntemi bilmiyordum.
- İşlem hatası yaptım.
- Dikkatim dağıldı.

seçenekleri sunulur.

İsteğe bağlı:

- Sesli açıklama.
- Çözüm fotoğrafı.

AI:

1. Öğrenci açıklamasını analiz eder.
2. İlk hata noktasını bulur.
3. H1–H7 sınıflandırır.
4. Konuyu belirler.
5. Kazanımı belirler.
6. Beceri alanını belirler.
7. Müdahaleyi belirler.

## Boş bırakma

Öğrenci:

- Boş bırakma nedeni.
- Sesli açıklama.
- Çözüm fotoğrafı.

ekleyebilir.

---

# 8. AI ANALİZ JSON STANDARDI

Örnek:

```json
{
  "error_type": "H3",
  "subject": "Matematik",
  "topic": "Üslü İfadeler",
  "learning_outcome": "...",
  "skill": "Bilgiyi problem içinde yorumlama",
  "confidence": 0.82,
  "intervention": "TOPIC_REVIEW",
  "video_needed": true,
  "reinforcement_question_count": 5
}
```

Müdahale türleri:

```text
QUICK_EXPLANATION
TOPIC_REVIEW
VIDEO
REINFORCEMENT
RETEST
STRATEGY_TRAINING
ERROR_ANALYSIS
DIFFICULTY_DOWN
DIFFICULTY_UP
```

---

# 9. KONU ÇALIŞ SİSTEMİ

Temel akış:

```text
Hata
 ↓
Konu
 ↓
Kazanım
 ↓
Beceri
 ↓
Kısa AI açıklaması
 ↓
MEB / doğrulanmış kaynak
 ↓
YouTube önerisi
 ↓
Örnek
 ↓
5–10 pekiştirme sorusu
 ↓
Mini test
 ↓
Mastery güncelleme
```

Öğrenci yalnızca video izledi diye “öğrendi” kabul edilmez.

Öğrenme mini test ile doğrulanmalıdır.

---

# 10. KAYNAK SİSTEMİ

Kaynak metadata:

```text
source_id
source_type
subject
grade
unit
topic
learning_outcome
skill
level
source_title
source_url
file_path
page
curriculum_version
academic_year
```

Kaynak türleri:

```text
MEB
REAL_LGS
MEB_SAMPLE
VERIFIED
YOUTUBE
AI_GENERATED
AI_PERSONALIZED
```

AI içeriği hiçbir zaman MEB içeriği gibi sunulmaz.

---

# 11. YOUTUBE SİSTEMİ

AI önce öğrencinin ihtiyacını belirler.

Örnek:

```text
H3
Üslü ifadeler
Problem içinde yorumlama
```

Sonra video araması yapılır.

Filtreler:

- Konu uyumu.
- 8. sınıf seviyesi.
- LGS ilişkisi.
- Türkçe.
- Erişilebilirlik.
- Süre.
- Eğitim kalitesi.

AI kendi başına uydurma URL üretmemelidir.

Önerilen sonuç sayısı:

**1–3 video**

---

# 12. HAFTALIK TEST SİSTEMİ

Başlangıç örneği:

```text
Matematik     10
Türkçe         8
Fen            6
İngilizce      2
Din            2
İnkılap        2
----------------
Toplam        30
```

Adaptif başlangıç:

```text
%50 zayıf alanlar
%30 güncel/recent konular
%20 karma LGS tekrar
```

Bu oranlar sabit değildir.

Öğrenci verisi geldikçe sistem dağılımı değiştirir.

---

# 13. 5 HAFTALIK DENEME

Her 5 haftada:

**Özgün LGS benzeri deneme**

özellikleri:

- Son 5 haftanın performansını kullanır.
- Öğrenci seviyesine göre hazırlanır.
- Gerçek LGS sorularını kopyalamaz.
- LGS becerilerine uygun olur.
- Zayıf ve güçlü alanları dengeli ölçer.
- Sonuç sonrası yeni 5 haftalık plan üretir.

---

# 14. SPACED REPETITION

Başlangıç:

```text
1 gün
3 gün
7 gün
14 gün
30 gün
```

Başarıya göre adaptif:

```text
Başarısız → erken tekrar
Orta → normal tekrar
Yüksek → daha uzun aralık
```

---

# 15. SORU ÜRETİM PIPELINE

```text
AI üretir
 ↓
JSON validation
 ↓
Müfredat kontrolü
 ↓
Seviye kontrolü
 ↓
Tek doğru cevap kontrolü
 ↓
Çözüm doğrulama
 ↓
Duplicate / similarity kontrolü
 ↓
Öğrenciye gönder
```

Gerçek LGS sorularında answer key doğrulanmış veri kaynağından gelir.

---

# 16. AI MİMARİSİ

```text
Student Profile
Curriculum
Question Bank
Answer History
Error History
Mastery
Resources
Review Schedule
        ↓
AI ORCHESTRATOR
        ↓
OpenRouter
        ↓
LLM
        ↓
Structured JSON
        ↓
Validation
        ↓
Student UI
```

AI rolleri:

- Question Analyzer.
- Teacher.
- Question Generator.
- Topic Explainer.
- Learning Coach.
- Weekly Exam Planner.

Model bağımsızlığı korunur.

Mevcut:

```text
OPENROUTER_MODEL=openrouter/free
```

---

# 17. MOTİVASYON SİSTEMİ

AI sahte övgü kullanmaz.

Kötü performansta:

Yanlış:
> Harikasın!

Doğru yaklaşım:

> H3 hataların bu hafta azalmış; ancak problem içindeki bilgileri ilişkilendirme hâlâ çalışma alanımız. Şimdi 5 soruluk kısa bir tekrar yapalım.

Motivasyon gerçek verilere dayanır:

- Başarı.
- Gelişim.
- Çalışma serisi.
- Tamamlanan hedef.
- Hata çözümü.
- Süreklilik.
- Mastery artışı.

---

# 18. GAMIFICATION

## XP

Örnek:

```text
10 soru                 +10 XP
Hata analizi             +5 XP
Sesli açıklama            +5 XP
Konu tekrarı             +15 XP
Video + mini test        +15 XP
Günlük hedef             +20 XP
Haftalık test            +30 XP
5 haftalık deneme        +50 XP
Zayıf konu gelişimi      +25 XP
```

XP farming engellenir.

## Oyun hakkı

Örnek:

```text
20 XP  → 2 dk
50 XP  → 5 dk
100 XP → yeni seviye
```

Günlük:

```text
Maksimum 10 dakika
Maksimum 2 oyun oturumu
```

Oyun öğrenmenin yerine geçmez.

---

# 19. ROZETLER

Örnek:

- İlk Adım
- 7 Gün
- Hata Dedektifi
- Konu Ustası
- Sınavcı
- 5 Haftalık Seri
- Seviye Atladım

Rozetler gerçek davranışlara bağlanmalıdır.

---

# 20. KARAKTER SİSTEMİ

Onboarding:

- Erkek.
- Kız.

Daha sonra değiştirilebilir.

Karakter:

- XP.
- Seviye.
- Rozet.
- Aksesuar.
- Oda eşyası.
- Öğrenme ilerlemesi.

Hedef görsel stil:

- Premium pastel mor/mavi.
- Gerçekçi 3D/humanoid.
- Modern eğitim platformu.
- Çalışma odası.
- Karakter gelişimi.

---

# 21. UI MİMARİSİ

Ana navigasyon:

```text
Ana Sayfa
Çalış
AI Koç
Dersler
Sınavlar
Kaynaklar
Ödüller
İlerleme
Profil
```

Ana sayfa:

- Öğrenci adı.
- Seviye.
- Avatar.
- XP.
- Seri.
- Bugünün görevleri.
- Haftalık hedef.
- AI Koç.
- Konu başarıları.
- Hata analizi.
- İlerleme grafiği.
- Oyun.
- Karakter gelişimi.

En önemli CTA:

**Şimdi ne yapmalıyım?**

---

# 22. SES SİSTEMİ

Kontroller:

```text
Başlat
Duraklat
Devam Et
Durdur
Tekrar Kaydet
Dinle
Kullan
```

Maksimum:

**60 saniye**

Teknik:

`MediaRecorder` gerçek ses kaydını yönetir.

SpeechRecognition yalnızca transkripsiyon için kullanılabilir.

SpeechRecognition sessizlik/nefes nedeniyle durduğunda gerçek kayıt sonlanmamalıdır.

---

# 23. FOTOĞRAF SİSTEMİ

Çözüm fotoğrafı:

- Yalnızca analiz için.
- Kalıcı saklama yok.
- Profilde saklama yok.
- DB'de kalıcı kayıt yok.
- Backup'a dahil değil.

Upload öncesi:

> 🔒 Gizlilik Bilgilendirmesi: Gönderdiğin ses kaydı veya çözüm fotoğrafı yalnızca bu sorudaki hatanı analiz etmek için kullanılacaktır. Analiz tamamlandıktan sonra dosya kalıcı olarak silinecektir ve öğrenci profilinde saklanmayacaktır.

Analiz sonrası:

> ✓ Analiz tamamlandı. Ses kaydın/fotoğrafın analiz için kullanıldı ve kalıcı olarak silindi.

Bu davranış backend'de fiziksel silmeyle uygulanmalıdır.

---

# 24. VERİTABANI

Önerilen tablolar:

```text
users
students
student_profiles
questions
answers
error_analyses
topics
learning_outcomes
resources
videos
weekly_exams
exam_attempts
exam_questions
mastery
study_sessions
review_schedule
achievements
xp_events
game_sessions
```

Öğrenci verileri GitHub'a konulmaz.

---

# 25. TEKNİK STACK

Mevcut:

```text
Next.js
App Router
TypeScript
CSS / Tailwind
Node.js
```

Planlanan:

```text
PostgreSQL
Prisma
Supabase
OpenRouter
Vercel
GitHub
Auth.js / NextAuth
Zustand gerektiğinde
React Query gerektiğinde
```

---

# 26. GELİŞTİRME ORTAMI

```text
Pop!_OS 22.04 LTS
64-bit
GNOME 42.9
Intel i7-8750H
32 GB RAM
NVIDIA Quadro P600 Mobile

Node.js 22.20.0
npm 10.9.3

Proje:
~/lgs-ai-coach
```

Her komutta klasör belirtilmelidir:

```text
Klasör: ~/lgs-ai-coach
```

---

# 27. ENV / API

`.env.local`:

```text
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=openrouter/free
```

API key:
- GitHub'a gönderilmez.
- Kod içine hard-code edilmez.
- Kullanıcıdan tekrar istenmez.

`.gitignore`:

```text
.env
.env.local
node_modules
.next
```

OpenRouter endpoint:

```text
https://openrouter.ai/api/v1
```

---

# 28. GITHUB / PRODUCTION

```text
GitHub
   ↓
Vercel
   ↓
Next.js
   ↓
Supabase/PostgreSQL
   ↓
OpenRouter
```

Öğrencinin Node/npm/Git/Python kurmasına gerek olmamalıdır.

Local bilgisayar development/test içindir.

Production cloud olmalıdır.

---

# 29. SYSTEMD

Mevcut service:

```text
~/.config/systemd/user/lgs-ai-coach.service
```

Restart:

```bash
systemctl --user restart lgs-ai-coach.service
```

Status:

```bash
systemctl --user status lgs-ai-coach.service
```

Log:

```bash
journalctl --user -u lgs-ai-coach.service -n 50 --no-pager
```

---

# 30. VERİ / MASTERY

Her öğrenci için:

```text
mastery
confidence
error_frequency
last_review
next_review
difficulty_response
question_time
blank_rate
study_time
streak
completion
review_success
```

Amaç öğrenciyi cezalandırmak değil, öğrenme kararını iyileştirmektir.

---

# 31. TIME MANAGEMENT

Takip:

- Soru süresi.
- Toplam test süresi.
- Konu süresi.
- Uzun beklenen sorular.
- Gereksiz süre.

Kullanım:

- Zaman yönetimi.
- Soru stratejisi.

Ceza mekanizması olarak kullanılmaz.

---

# 32. MVP

İlk gerçek MVP:

1. Öğrenci profili.
2. Soru çözme.
3. Cevap kaydı.
4. Metin tabanlı hata analizi.
5. Konu tekrar.
6. Basit ilerleme.

Sonraya bırakılabilir:

- 3D karakter.
- Gelişmiş oyunlar.
- Ses.
- Fotoğraf.
- Parent panel.
- Gelişmiş denemeler.

---

# 33. GÜVENLİK

- HTTPS.
- Authentication.
- Authorization.
- Rate limiting.
- Secret management.
- Input validation.
- AI output validation.
- Prompt injection koruması.
- DB isolation.
- Logging.
- Error monitoring.
- Backup.
- Deletion.

AI:
- Kaynak uydurmaz.
- MEB olmayan içeriği MEB diye sunmaz.
- Gerçek LGS sorusunu kopyalamaz.
- Doğrulanmamış answer key üretmez.
- Öğrenciyi kişilik özelliğiyle etiketlemez.
- Sahte motivasyon kullanmaz.

---

# 34. KVKK / ÇOCUK GİZLİLİĞİ

Production öncesi:

- KVKK değerlendirmesi.
- Çocuk verisi değerlendirmesi.
- Ebeveyn onayı.
- Veri minimizasyonu.
- Retention/deletion politikası.
- AI sağlayıcı veri işleme kapsamı.
- Privacy Policy.
- Terms.
- Consent kayıtları.

Hedef ülkelere göre ayrıca hukuk incelemesi yapılmalıdır.

---

# 35. TEST STRATEJİSİ

## Unit
- H1–H7.
- XP.
- Mastery.
- Review schedule.

## Integration
- Question → Answer.
- Answer → Error Analysis.
- Error → Intervention.
- Intervention → Mastery.

## E2E
- Onboarding.
- Soru.
- Yanlış cevap.
- Hata analizi.
- Konu.
- Haftalık test.
- Oyun.
- Profil.

## AI
- JSON schema.
- Hallucination.
- Wrong answer.
- Invalid question.
- Duplicate.
- Curriculum compliance.

---

# 36. REPO YAPISI

```text
lgs-ai-coach/
├── app/
├── components/
├── lib/
│   ├── ai/
│   ├── curriculum/
│   ├── questions/
│   ├── mastery/
│   └── gamification/
├── data/
│   ├── curriculum/
│   ├── questions/
│   ├── sources/
│   └── videos/
├── prisma/
├── public/
│   ├── avatars/
│   └── ...
├── docs/
│   ├── SYSTEM-SPEC.md
│   ├── CURRICULUM.md
│   ├── QUESTION-SYSTEM.md
│   ├── COACHING-SYSTEM.md
│   ├── RESOURCE-SYSTEM.md
│   └── PRIVACY.md
├── .env.example
├── .gitignore
└── package.json
```

---

# 37. FAZ 0 — STABİLİZASYON

Amaç:
Mevcut UI'yi bozmayacak sağlam bir temel.

Checklist:

- [x] Next.js build.
- [x] TypeScript.
- [x] Dashboard.
- [x] Profil.
- [x] Navigation.
- [x] Çalış ekranı.
- [x] AI Koç.
- [x] İlerleme.
- [x] Ödüller.
- [x] Oyun Merkezi.
- [x] Buton/event testleri.
- [ ] Responsive test.
- [ ] Runtime error audit.
- [ ] Accessibility audit.

Her değişiklik sonrası:

```bash
cd ~/lgs-ai-coach
npm run build
```

---

# 38. FAZ 1 — GERÇEK OYUNLAR

## 38.1 Hafıza Kartları

Hedef:

- 12 kart.
- 6 çift.
- Kart çevirme.
- Eşleşme.
- Yanlış eşleşmede kapanma.
- Hamle sayısı.
- Süre.
- Tamamlanma mesajı.
- Yeniden başlat.
- Geri dön.

Oyun öğrenme davranışını desteklemelidir.

## 38.2 Mini 2048

Hedef:

- 4×4.
- Yukarı.
- Aşağı.
- Sağ.
- Sol.
- Birleşme.
- Skor.
- Reset.
- Game over.
- Kazanma durumu.

## 38.3 Oyun ekonomisi

- XP'den oyun hakkı.
- Günlük maksimum süre.
- Session kaydı.
- XP farming önleme.

---

# 39. FAZ 2 — SORU VERİ MODELİ

Question schema:

```text
id
subject
grade
unit
topic
learning_outcome
skill
difficulty
question_text
options
correct_answer
solution
source_type
source_id
year
tags
verified
created_at
```

Ek metadata:

```text
estimated_time
lgs_skill
curriculum_version
similarity_hash
```

---

# 40. FAZ 3 — SORU BANKASI

Kaynak sınıfları:

```text
REAL_LGS
MEB_SAMPLE
VERIFIED
ORIGINAL
AI_PERSONALIZED
```

Gerçek LGS:

- Answer key doğrulanmış.
- Kaynak yılı.
- Ders.
- Konu.
- Kazanım.
- Beceri.

AI-generated:

- Özgün.
- Doğrulanmış.
- Tek doğru.
- Çözümü doğrulanmış.
- Duplicate kontrolü yapılmış.

---

# 41. FAZ 4 — ANSWER TRACKING

Her cevap:

```text
student_id
question_id
attempt_id
selected_answer
is_correct
time_spent
blank
error_reason
created_at
```

İleride:

```text
voice_analysis_id
image_analysis_id
error_analysis_id
```

---

# 42. FAZ 5 — GERÇEK AI HATA ANALİZİ

Endpoint örneği:

```text
POST /api/ai/analyze
```

Input:

```text
question
student_answer
correct_answer
student_reason
transcript
solution_image
student_context
```

Output:

```json
{
  "error_type": "H3",
  "topic": "Üslü İfadeler",
  "learning_outcome": "...",
  "skill": "...",
  "confidence": 0.82,
  "intervention": "TOPIC_REVIEW"
}
```

Çıktı JSON schema ile doğrulanır.

---

# 43. FAZ 6 — CURRICULUM ENGINE

Müfredat hiyerarşisi:

```text
Ders
 ↓
Ünite
 ↓
Konu
 ↓
Kazanım
 ↓
Beceri
```

Sistem soruyu curriculum node'a bağlar.

Böylece:

```text
Hata
→ Topic
→ Learning Outcome
→ Skill
```

ilişkisi kurulabilir.

---

# 44. FAZ 7 — RESOURCE ENGINE

Kaynak türleri:

- MEB.
- MEB PDF.
- MEB örnek soru.
- YouTube.
- AI summary.
- Internal resource.

Kaynak güven düzeyi:

```text
AUTHORITATIVE
VERIFIED
AI_GENERATED
```

---

# 45. FAZ 8 — ADAPTIVE LEARNING

Mastery başlangıç örneği:

```text
0–39  → zayıf
40–59 → gelişiyor
60–79 → yeterli
80–100 → güçlü
```

Bu eşikler gerçek veriler geldikçe optimize edilir.

Sistem:

- Hata sıklığı.
- Son başarı.
- Son tekrar.
- Soru zorluğu.
- Süre.
- Benzer soru performansı.

ile sonraki soruyu seçer.

---

# 46. FAZ 9 — AI KOÇ

AI Koç günlük:

```text
Bugünkü hedef
Zayıf konu
Tekrar zamanı
Önerilen soru
Motivasyon
Çalışma süresi
```

Örnek:

```text
Bugün:

1. Üslü ifadeler — 5 dk tekrar
2. 5 pekiştirme sorusu
3. 5 soruluk mini test
4. H3 tekrar kontrolü
```

---

# 47. FAZ 10 — HAFTALIK TEST ENGINE

Her hafta:

1. Öğrenci verisi toplanır.
2. Zayıf konular belirlenir.
3. Son öğrenilen konular eklenir.
4. Karma tekrar eklenir.
5. 30 soru oluşturulur.
6. Test uygulanır.
7. Hata analizi yapılır.
8. Haftalık rapor oluşturulur.
9. Sonraki hafta planlanır.

---

# 48. FAZ 11 — 5 HAFTALIK DENEME ENGINE

Input:

```text
last_5_weeks
mastery
error_history
question_history
time_management
```

Output:

```text
LGS-like mock
```

Sonuç:

- Ders bazlı başarı.
- Konu bazlı başarı.
- Hata türleri.
- Süre.
- Boşlar.
- Son 5 haftayla karşılaştırma.
- Yeni çalışma planı.

---

# 49. FAZ 12 — VOICE BACKEND

Akış:

```text
Browser
 ↓
Temporary upload
 ↓
STT / AI analysis
 ↓
Derived result
 ↓
Delete file
 ↓
Confirm deletion
```

Kalıcı ses saklama yok.

---

# 50. FAZ 13 — IMAGE ANALYSIS

Çözüm fotoğrafı:

```text
Upload
 ↓
Temporary storage
 ↓
Vision analysis
 ↓
Error analysis
 ↓
Derived learning data
 ↓
Delete original
```

Kalıcı görüntü saklanmaz.

---

# 51. FAZ 14 — GAMIFICATION ENGINE

Tables:

```text
achievements
xp_events
game_sessions
reward_unlocks
character_items
```

XP olayları audit edilebilir olmalıdır.

Örnek:

```text
XP_EVENT:
student_id
event_type
amount
source_id
created_at
```

---

# 52. FAZ 15 — 3D KARAKTER

Mevcut SVG avatarlar geçici prototiptir.

Üretim hedefi:

- Gerçekçi 3D/humanoid.
- Erkek/kız.
- Birden fazla saç.
- Kıyafet.
- Aksesuar.
- İfade.
- Çalışma odası.
- Seviye bazlı gelişim.

Karakter öğrenme ilerlemesinin görsel temsilidir.

---

# 53. FAZ 16 — AUTHENTICATION

Öğrenci:

- Login.
- Profile.
- Progress.

Parent:

- Parent login.
- Student relationship.
- Consent.
- High-level progress.

Yetkilendirme:

Öğrenci başka öğrencinin verisini göremez.

---

# 54. FAZ 17 — SUPABASE / POSTGRESQL

Kurulum:

- Database.
- Prisma schema.
- Migrations.
- Indexes.
- RLS.
- Backup.
- Delete policy.

Önemli:

Çocuk verileri için erişim izolasyonu zorunludur.

---

# 55. FAZ 18 — SECURITY

Uygulanacak:

- HTTPS.
- Secrets.
- Auth.
- Authorization.
- Rate limiting.
- Input validation.
- Output validation.
- Prompt injection protection.
- File upload limits.
- MIME validation.
- Size limits.
- DB RLS.
- Error monitoring.

---

# 56. FAZ 19 — KVKK / PRIVACY

Production öncesi:

- Privacy policy.
- Terms.
- Parent consent.
- Data minimization.
- Retention.
- Deletion.
- AI provider data handling.
- Child data controls.
- Data export/deletion procedures.

Hedef ülkeler için ayrıca hukuk incelemesi yapılır.

---

# 57. FAZ 20 — PRODUCTION

Architecture:

```text
GitHub
 ↓
Vercel
 ↓
Next.js
 ↓
Supabase
 ↓
OpenRouter
```

Production checklist:

- Domain.
- HTTPS.
- Environment variables.
- Database.
- Auth.
- Monitoring.
- Error tracking.
- Backup.
- Rate limits.
- Privacy.
- Terms.
- Consent.
- Delete workflows.

---

# 58. TEST STRATEJİSİ

## Unit

- H1–H7.
- XP.
- Mastery.
- Review.
- Question validation.

## Integration

- Question → Answer.
- Answer → Error.
- Error → Intervention.
- Intervention → Mastery.
- Upload → Analyze → Delete.

## E2E

- Register.
- Login.
- Onboarding.
- Question.
- Wrong answer.
- Voice.
- Image.
- Topic review.
- Weekly test.
- Game.
- Profile.
- Parent.

## Load

- API rate.
- Concurrent students.
- AI request limits.
- DB performance.

---

# 59. OBSERVABILITY

Production:

- Error monitoring.
- Request logs.
- AI latency.
- AI failures.
- DB latency.
- Upload failures.
- Delete failures.

Privacy nedeniyle loglara:

- Ses dosyası.
- Çözüm fotoğrafı.
- Çocukların gereksiz kişisel verileri

yazılmaz.

---

# 60. CI/CD

GitHub:

```text
feature branch
 ↓
Pull Request
 ↓
Build
 ↓
TypeScript
 ↓
Tests
 ↓
Review
 ↓
main
 ↓
Vercel
```

Her PR'da en az:

```bash
npm run build
```

çalışmalıdır.

---

# 61. GÖREV YÖNETİMİ

Her özellik:

```text
TODO
IN_PROGRESS
TESTING
DONE
```

durumlarından geçmelidir.

Bir özellik:

- Kodlandı.
- Build başarılı.
- Browser test başarılı.
- Kritik hata yok.

olmadan DONE sayılmaz.

---

# 62. MEVCUT DURUM

Şu anda doğrulanmış:

```text
[✓] Next.js
[✓] TypeScript
[✓] Dashboard
[✓] Profil
[✓] Avatar
[✓] Çalış
[✓] Soru ekranı
[✓] AI Koç
[✓] İlerleme
[✓] Ödüller
[✓] Oyun Merkezi
[✓] Navigation
[✓] Build
[✓] Event testleri
[✓] Hafıza Kartları event testi
[✓] Mini 2048 event testi
```

Geçici:

```text
[ ] Gerçek Hafıza Kartları
[ ] Gerçek Mini 2048
```

---

# 63. BİR SONRAKİ ADIM

İlk iş:

**`alert()` testlerini kaldırıp gerçek Hafıza Kartları oyununu eklemek.**

Sonra:

**Gerçek Mini 2048.**

Sonra:

**XP + oyun session sistemi.**

Sonra:

**Gerçek soru bankası ve question schema.**

---

# 64. GELİŞTİRME SIRASI — MASTER

```text
[✓] UI Prototype
[✓] Navigation
[✓] Profile
[✓] Study Flow
[✓] AI Coach UI
[✓] Progress UI
[✓] Rewards UI
[✓] Game Center UI
[✓] Button/Event Testing

[ ] Real Memory Game
[ ] Real Mini 2048
[ ] XP/Game Economy
[ ] Question Schema
[ ] Question Bank
[ ] Answer Tracking
[ ] H1-H7 Analysis Engine
[ ] Curriculum DB
[ ] Topic Resource Library
[ ] YouTube Pipeline
[ ] Adaptive Learning
[ ] Spaced Repetition
[ ] Weekly Test Engine
[ ] 5-Week Mock Engine
[ ] Voice Backend
[ ] Image Analysis
[ ] Automatic File Deletion
[ ] Authentication
[ ] Parent System
[ ] Supabase/PostgreSQL
[ ] Security Layer
[ ] KVKK/Child Privacy
[ ] 3D Character System
[ ] Production Monitoring
[ ] Vercel Deployment
[ ] Production Launch
```

---

# 65. GELİŞTİRME İLKELERİ

1. Önce çalışan sistemi koru.
2. Büyük dosya değişikliklerinden kaçın.
3. Her kritik değişiklik öncesi backup al.
4. Her değişiklikten sonra build çalıştır.
5. Build başarılı olmadan sonraki faza geçme.
6. Gerçek kullanıcı verisini GitHub'a koyma.
7. AI çıktısını validate et.
8. Gerçek LGS answer key'i AI'ya bırakma.
9. Öğrenciyi yalnızca doğru/yanlış üzerinden değerlendirme.
10. İlk hata noktasını bul.
11. Video izlemeyi öğrenme kabul etme; retest yap.
12. Gamification öğrenmenin yerine geçmesin.
13. Motivasyonu gerçek veriye bağla.
14. Ses/fotoğrafı kalıcı saklama.
15. Üretime geçmeden KVKK/çocuk gizliliğini tamamla.

---

# 66. KRİTİK ÜRÜN KARARLARI

### Karar 1
LGS sistemi 2018+ gerçek sınavları esas alır.

### Karar 2
H1–H7 hata modeli merkezi öğrenme analitiğidir.

### Karar 3
Öğrenci seviyesi ve soru zorluğu ayrı tutulur.

### Karar 4
Video izleme öğrenme kanıtı değildir; mini test gerekir.

### Karar 5
AI gerçek LGS answer key'ini üretmez.

### Karar 6
Ses/fotoğraf analiz sonrası kalıcı olarak silinir.

### Karar 7
AI motivasyonu gerçek ilerlemeye dayanır.

### Karar 8
Oyun öğrenme hedeflerinden sonra ve süre sınırıyla çalışır.

### Karar 9
Local makine development/test içindir.

### Karar 10
Production cloud üzerinde çalışır.

---

# 67. NİHAİ ÜRÜN TANIMI

Hedef ürün:

**Kişiselleştirilmiş AI LGS Öğrenme Koçu**

Öğrenciye şu soruların tamamına cevap verebilmelidir:

- Ne çalışmalıyım?
- Neden çalışmalıyım?
- Hangi seviyedeyim?
- Nerede hata yapıyorum?
- Hatanın ilk noktası ne?
- Nasıl düzelteceğim?
- Ne zaman tekrar edeceğim?
- Şimdi hangi soruyu çözmeliyim?
- Bu konuyu gerçekten öğrendim mi?
- Bir sonraki haftada neye odaklanmalıyım?

---

# 68. MASTER ROADMAP

```text
UI
 ↓
ETKİLEŞİM
 ↓
OYUNLAR
 ↓
SORU BANKASI
 ↓
CEVAP TAKİBİ
 ↓
HATA ANALİZİ
 ↓
MÜFREDAT
 ↓
KAYNAKLAR
 ↓
AI KOÇ
 ↓
ADAPTİF ÖĞRENME
 ↓
HAFTALIK TEST
 ↓
5 HAFTALIK DENEME
 ↓
SES/FOTOĞRAF
 ↓
GAMIFICATION
 ↓
3D KARAKTER
 ↓
AUTH
 ↓
DATABASE
 ↓
SECURITY
 ↓
KVKK
 ↓
PRODUCTION
```

---

# 69. PROJE BİTİŞ KRİTERİ

Proje ancak aşağıdakiler tamamlandığında production-ready kabul edilir:

- Gerçek soru bankası.
- Doğrulanmış answer key.
- H1–H7 AI analizi.
- Curriculum mapping.
- Adaptive mastery.
- Spaced repetition.
- Haftalık test.
- 5 haftalık deneme.
- Voice/image geçici işleme.
- Fiziksel dosya silme.
- Authentication.
- Parent/consent.
- PostgreSQL/Supabase.
- RLS.
- Security.
- KVKK/privacy.
- Monitoring.
- Backup.
- E2E tests.
- Production deployment.

---

# 70. SON NOT

Bu belge proje için tek master roadmap olarak kullanılmalıdır.

Yeni bir özellik eklendiğinde:

1. İlgili faz bulunur.
2. Görev TODO olarak eklenir.
3. Kodlanır.
4. Build edilir.
5. Browser test edilir.
6. Gerekirse test yazılır.
7. `[ ]` → `[✓]` yapılır.
8. Sonraki göreve geçilir.

**Ana hedef: hızlı kod yazmak değil, güvenilir ve ölçülebilir bir öğrenme sistemi oluşturmaktır.**
