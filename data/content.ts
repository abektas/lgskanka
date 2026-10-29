/**
 * Uygulamada sayfalar arasında paylaşılan içerik.
 * (Demo veri. Sonraki adım: bu kayıtların `/api/*` üzerinden gelmesi.)
 */

export type Tone = "pembe" | "mavi" | "mint" | "limon" | "lavanta" | "seftali";

export type Subject = {
  name: string;
  slug: string;
  icon: string;
  tone: Tone;
  score: number;
  delta: number;
  topics: string[];
};

export const subjects: Subject[] = [
  {
    name: "Matematik",
    slug: "matematik",
    icon: "🧮",
    tone: "pembe",
    score: 72,
    delta: 6,
    topics: ["Üslü İfadeler", "Kareköklü İfadeler", "Cebirsel İfadeler", "Veri Analizi", "Olasılık"],
  },
  {
    name: "Türkçe",
    slug: "turkce",
    icon: "📖",
    tone: "mavi",
    score: 81,
    delta: 3,
    topics: ["Sözcükte Anlam", "Cümlede Anlam", "Paragraf", "Fiilimsiler", "Yazım Kuralları"],
  },
  {
    name: "Fen Bilimleri",
    slug: "fen",
    icon: "🔬",
    tone: "mint",
    score: 64,
    delta: 12,
    topics: ["Mevsimler ve İklim", "DNA ve Kalıtım", "Basınç", "Madde ve Endüstri", "Basit Makineler"],
  },
  {
    name: "İngilizce",
    slug: "ingilizce",
    icon: "🌍",
    tone: "lavanta",
    score: 78,
    delta: 4,
    topics: ["Friendship", "Teen Life", "In the Kitchen", "On the Phone", "The Internet"],
  },
  {
    name: "İnkılap Tarihi",
    slug: "inkilap-tarihi",
    icon: "🏛️",
    tone: "seftali",
    score: 60,
    delta: 10,
    topics: ["Osmanlı Devleti", "Türkiye Kurtuluş Savaşı", "Cumhuriyetin İlanı", "Atatürk Dönemi", "Çağdaş Türkiye"],
  },
  {
    name: "Din Kültürü",
    slug: "din-kulturu",
    icon: "☪️",
    tone: "limon",
    score: 58,
    delta: 8,
    topics: ["Kur'an", "Hz. Muhammed", "İbadetler", "Ahlak", "Müslüman Türkler"],
  },
];

export type Task = {
  id: string;
  icon: string;
  title: string;
  detail: string;
  xp: number;
  href: string;
  minutes: number;
};

export const tasks: Task[] = [
  {
    id: "matematik-uslu",
    icon: "🎯",
    title: "Matematik – Üslü İfadeler",
    detail: "10 soru + hata analizi",
    xp: 10,
    href: "/calis",
    minutes: 15,
  },
  {
    id: "konu-tekrar",
    icon: "📘",
    title: "Konu Tekrarı",
    detail: "Kısa video + mini test",
    xp: 15,
    href: "/pekistirme",
    minutes: 12,
  },
  {
    id: "mini-test",
    icon: "📝",
    title: "Haftalık Mini Test",
    detail: "20 soru · karışık konular",
    xp: 20,
    href: "/haftalik-test",
    minutes: 25,
  },
];

export type ErrorType = {
  code: "H1" | "H2" | "H3" | "H4" | "H5" | "H6" | "H7";
  name: string;
  /**
   * AI teşhis isteminde kullanılan kısa etiket (tek teknik H kaynağı).
   * Öğrenciye gösterilmez; yetkili sözlük Master Plan §6'dır.
   */
  promptHint: string;
  color: string;
  share: number;
  definition: string;
  advice: string;
};

/** H1–H7 hata taksonomisi: kankanın teşhis ettiği hata türleri. */
export const errorTypes: ErrorType[] = [
  {
    code: "H1",
    name: "Kavram eksikliği",
    promptHint: "kavram",
    color: "#FF7BAC",
    share: 18,
    definition: "Konu bilgisi eksik ya da yanlış öğrenilmiş.",
    advice: "Önce konu özetini oku, sonra aynı kazanımdan 5 kolay soru çöz.",
  },
  {
    code: "H2",
    name: "Yöntem / strateji",
    promptHint: "yöntem/strateji",
    color: "#FF9A5A",
    share: 22,
    definition: "Konuyu biliyorsun ama çözüm yolunu seçemiyorsun.",
    advice: "Soru tipini tanımla: verilen ne, istenen ne? Adımları yaz.",
  },
  {
    code: "H3",
    name: "Okuma / modelleme",
    promptHint: "okuduğunu anlama/modelleme",
    color: "#3D8BFF",
    share: 28,
    definition: "Metni veya görseli yanlış yorumlayıp model kuramama.",
    advice: "Soruyu kendi cümlenle yeniden yaz, verileri tabloya dök.",
  },
  {
    code: "H4",
    name: "İşlem hatası",
    promptHint: "işlem",
    color: "#16B98A",
    share: 32,
    definition: "Yol doğru, hesaplama kayıyor.",
    advice: "İşlemi iki kez kontrol et; kâğıtta alt alta yaz.",
  },
  {
    code: "H5",
    name: "Gereksiz bilgi",
    promptHint: "gereksiz bilgiyi ayıklama",
    color: "#9A65F5",
    share: 12,
    definition: "Sorudaki fazladan bilgiye takılmak.",
    advice: "Önce isteneni belirle, sonra gereken veriyi işaretle.",
  },
  {
    code: "H6",
    name: "İlişkilendirme",
    promptHint: "bilgileri ilişkilendirme",
    color: "#F5B93E",
    share: 24,
    definition: "Bilgileri birbiriyle bağlayamama.",
    advice: "Birden çok konu geçen sorularda ara adımları yaz.",
  },
  {
    code: "H7",
    name: "Dikkat",
    promptHint: "dikkat",
    color: "#FF6B6B",
    share: 15,
    definition: "Hızlı okuma veya acele kaynaklı hata.",
    advice: "25 dakikada 5 soru; son 2 dakikada sadece kontrol.",
  },
];

/**
 * AI teşhis istemindeki H1–H7 sözlüğü — `errorTypes`'ten **türetilir**.
 *
 * Teknik olarak tek kaynak `errorTypes` dizisidir; istemde ikinci bir kod sözlüğü
 * elle yazılmaz. Sıra ve anlam Master Plan §6 ile `AGENTS.md` canonical
 * sözlüğüne göre kilitlidir (`tests/canonical-taxonomy/canonical-taxonomy.test.mjs`).
 */
export const errorCodePromptLine = `Hata kodlarından uygun olanı seç: ${errorTypes.map(
  (item) => `${item.code} ${item.promptHint}`,
).join(", ")}.`;

export type Badge = {
  icon: string;
  name: string;
  detail: string;
  earned: boolean;
};

export const badges: Badge[] = [
  { icon: "🌱", name: "İlk Adım", detail: "İlk görevini tamamladın", earned: true },
  { icon: "🔥", name: "4 Gün Seri", detail: "4 gün üst üste çalıştın", earned: true },
  { icon: "🔍", name: "İlk Hata Analizi", detail: "İlk hatanı birlikte çözdük", earned: true },
  { icon: "🧮", name: "İşlem Ustası", detail: "H4 hatan %10'un altına indi", earned: true },
  { icon: "🎯", name: "Hedefe Sadık", detail: "1 hafta plana uydun", earned: true },
  { icon: "📚", name: "Kitap Kurdu", detail: "50 soru çözdün", earned: true },
  { icon: "🚀", name: "Hızlı Düşünen", detail: "Testte ilk 10'a gir", earned: false },
  { icon: "🏆", name: "7 Gün Seri", detail: "7 gün üst üste çalış", earned: false },
];

export type Game = {
  icon: string;
  name: string;
  detail: string;
  minutes: number;
};

export const games: Game[] = [
  { icon: "🧠", name: "Hafıza Kartları", detail: "Kavramları eşleştir", minutes: 5 },
  { icon: "🔢", name: "Matematik 2048", detail: "Sayıları birleştir", minutes: 5 },
  { icon: "🏃", name: "LGS Runner", detail: "Doğru cevapla zıpla", minutes: 5 },
  { icon: "⚡", name: "Hız Oyunu", detail: "30 saniyede kaç soru?", minutes: 3 },
];

/** 5 haftalık deneme programı — haftalık deneme sınavı planı. */
export const examPlan = [
  { week: "1. Hafta", subject: "Sözel Bölüm", date: "6 Ekim", status: "done" as const },
  { week: "2. Hafta", subject: "Sayısal Bölüm", date: "13 Ekim", status: "done" as const },
  { week: "3. Hafta", subject: "Genel Deneme", date: "20 Ekim", status: "active" as const },
  { week: "4. Hafta", subject: "Sözel Bölüm", date: "27 Ekim", status: "upcoming" as const },
  { week: "5. Hafta", subject: "Genel Deneme", date: "3 Kasım", status: "upcoming" as const },
];

/**
 * Sınav sonuç ekranı için örnek görünüm verisi.
 * Gerçek öğrenci sonucu değildir; resmi puan/yüzdelik hesaplaması olarak kullanılmamalıdır.
 */
export const demoExamResults = [
  { label: "D1", net: 62.33, score: 366.4, percentile: 15.4 },
  { label: "D2", net: 65.0, score: 378.8, percentile: 13.2 },
  { label: "D3", net: 68.33, score: 393.6, percentile: 10.8 },
  { label: "D4", net: 71.0, score: 405.2, percentile: 8.9 },
  { label: "D5", net: 74.0, score: 417.01, percentile: 7.01 },
] as const;

export const demoExamSubjects = [
  { name: "Türkçe", net: 18, total: 20 },
  { name: "T.C. İnkılap Tarihi", net: 8, total: 10 },
  { name: "Din Kültürü", net: 9, total: 10 },
  { name: "İngilizce", net: 9.67, total: 10 },
  { name: "Matematik", net: 15.33, total: 20 },
  { name: "Fen Bilimleri", net: 14, total: 20 },
] as const;

export type Question = {
  id: string;
  subject: string;
  topic: string;
  text: string;
  options: string[];
  correct: number;
  skill: string;
  difficulty: 1 | 2 | 3;
  /** Her seçenek için kankanın ön teşhisi (doğru cevap dâhil). */
  explain: string;
};

export const questionBank: Question[] = [
// ============ MATEMATİK (10 soru) ============
  { id: "q-uslu-1", subject: "Matematik", topic: "Üslü İfadeler", text: "Aşağıdakilerden hangisi 2³ · 2⁵ işleminin sonucuna eşittir?", options: ["2⁸", "2¹⁰", "2¹²", "2¹⁵"], correct: 0, skill: "Bilgiyi problem içinde yorumlama", difficulty: 2, explain: "Aynı tabanlı üsler çarpılırken üsler toplanır: 2³ · 2⁵ = 2³⁺⁵ = 2⁸" },
  { id: "q-uslu-2", subject: "Matematik", topic: "Üslü İfadeler", text: "(3²)³ ifadesinin eşiti aşağıdakilerden hangisidir?", options: ["3⁵", "3⁶", "3⁹", "6³"], correct: 1, skill: "Kural uygulama", difficulty: 2, explain: "Üssün üssü alınırken üsler çarpılır: (3²)³ = 3²ˣ³ = 3⁶" },
  { id: "q-kok-1", subject: "Matematik", topic: "Kareköklü İfadeler", text: "√72 sayısı aşağıdakilerden hangisine eşittir?", options: ["6√2", "8√2", "4√3", "2√18"], correct: 0, skill: "Bilgiyi problem içinde yorumlama", difficulty: 3, explain: "72 = 36 · 2 olduğundan √72 = √36 · √2 = 6√2" },
  { id: "q-cebir-1", subject: "Matematik", topic: "Cebirsel İfadeler", text: "3x + 2 = 17 denkleminde x kaçtır?", options: ["3", "4", "5", "6"], correct: 2, skill: "Kural uygulama", difficulty: 1, explain: "3x = 15 → x = 5" },
  { id: "q-cebir-2", subject: "Matematik", topic: "Cebirsel İfadeler", text: "2(x + 3) - 4 = 10 eşitliğinde x kaçtır?", options: ["2", "3", "4", "5"], correct: 2, skill: "Kural uygulama", difficulty: 2, explain: "2x + 6 - 4 = 10 → 2x = 8 → x = 4" },
  { id: "q-veri-1", subject: "Matematik", topic: "Veri Analizi", text: "Bir sınıftaki 20 öğrencinin not ortalaması 70'dir. 80 notlu 2 öğrenci ayrılırsa yeni ortalama kaç olur?", options: ["68", "68.5", "69", "69.5"], correct: 1, skill: "Bilgileri ilişkilendirme", difficulty: 3, explain: "Toplam = 1400, 2 öğrenci (160) çıkar → 1240 / 18 = 68.88 ≈ 68.5" },
  { id: "q-veri-2", subject: "Matematik", topic: "Olasılık", text: "1-6 arası tek sayılı bir zar atılır. 3'ten büyük tek sayılar gelme olasılığı nedir?", options: ["1/6", "1/3", "1/2", "2/3"], correct: 2, skill: "Kural uygulama", difficulty: 2, explain: "Tek sayılar: 1,3,5. 3'ten büyük tek: 5. Olasılık = 1/3" },
  { id: "q-geometri-1", subject: "Matematik", topic: "Geometri", text: "İç açıları toplamı 180° olan üçgenin bir açısı 90°, diğeri 45° ise üçüncü açı kaç derecedir?", options: ["35°", "40°", "45°", "50°"], correct: 2, skill: "Bilgiyi problem içinde yorumlama", difficulty: 1, explain: "180 - 90 - 45 = 45°" },
  { id: "q-geometri-2", subject: "Matematik", topic: "Geometri", text: "Kenarı 8 cm olan bir karenin alanı kaç cm²dir?", options: ["32", "48", "64", "72"], correct: 2, skill: "Kural uygulama", difficulty: 1, explain: "Kare alanı = a² = 8² = 64 cm²" },
  { id: "q-geometri-3", subject: "Matematik", topic: "Geometri", text: "Yarıçapı 7 cm olan dairenin çevresi kaç cm'dir? (π = 22/7 alınız)", options: ["22", "44", "66", "88"], correct: 1, skill: "Kural uygulama", difficulty: 2, explain: "Çevre = 2πr = 2 × 22/7 × 7 = 44 cm" },

  // ============ TÜRKÇE (8 soru) ============
  { id: "q-tur-1", subject: "Türkçe", topic: "Sözcükte Anlam", text: "\"Elini taşın altına koymak\" deyiminin anlamı nedir?", options: ["Yardım etmek", "Sorumluluk almak", "Kendi işini yapmak", "Gizli saklamak"], correct: 1, skill: "Bilgiyi problem içinde yorumlama", difficulty: 2, explain: "Bu deyim, bir işin sorumluluğunu üstlenmek, yükü sırtlamak anlamına gelir." },
  { id: "q-tur-2", subject: "Türkçe", topic: "Sözcükte Anlam", text: "\"Ateşe bulutluk etmek\" deyimi hangi durumu anlatır?", options: ["Öfke uyuşması", "Olayı abartma", "Gizlice iş yapma", "Hızlı koşma"], correct: 1, skill: "Bilgiyi problem içinde yorumlama", difficulty: 2, explain: "Olayı gerçekten ne varsa daha büyüğü gibi göstermek, abartmak anlamına gelir." },
  { id: "q-tur-3", subject: "Türkçe", topic: "Cümlede Anlam", text: "\"Ali okula gitti ama Ayşe gitmedi.\" cümlesinde kullanılan bağlaç türü nedir?", options: ["İşteş", "Ayırıcı", "Bağlayıcı", "Ekler"], correct: 1, skill: "Kural uygulama", difficulty: 2, explain: "\"ama\" zıtlık bildiren ayırıcı bir bağlaçtır." },
  { id: "q-tur-4", subject: "Türkçe", topic: "Parçada Anlam", text: "Bir paragrafta ana fikri hangi cümle verir?", options: ["Giriş cümlesi", "Gelişme cümleleri", "Sonuç cümlesi", "Tüm cümleler eşit derecede"], correct: 0, skill: "Bilgiyi problem içinde yorumlama", difficulty: 2, explain: "Ana fikir genellikle giriş cümlesinde (konu cümlesinde) verilir." },
  { id: "q-tur-5", subject: "Türkçe", topic: "Fiilimsiler", text: "Okuma, yazma, koşma kelimeleri hangi fiilimsi türüdür?", options: ["Mastar", "Sıfat-fiil", "Zarf-fiil", "Bağlaç"], correct: 0, skill: "Kural uygulama", difficulty: 2, explain: "-ma/-me ekiyle yapılan fiilimsiler mastardır." },
  { id: "q-tur-6", subject: "Türkçe", topic: "Yazım Kuralları", text: "Aşağıdakilerden hangisi yazım kuralına uygun yazılmıştır?", options: ["Görüşlü", "Görüşlü", "Görüşlü", "Görüşlü"], correct: 0, skill: "Kural uygulama", difficulty: 1, explain: "Türkçede 'görüşlü' doğru yazımıdır (telaffuz bozulması önlenir)." },
  { id: "q-tur-7", subject: "Türkçe", topic: "Noktalama İşaretleri", text: "\"Ali, Ayşe, Fatma ve Ahmet sınıfa girdiler.\" cümlesinde virgüller neyi ayırır?", options: ["Bağlaçları", "Özneleri", "Yüklemleri", "Tümcecikleri"], correct: 1, skill: "Kural uygulama", difficulty: 2, explain: "Virgüller sıralı özneleri ayırmak için kullanılır." },
  { id: "q-tur-8", subject: "Türkçe", topic: "Söz Sanatları", text: "\"Güneş, dünyayı ısıtan bir topaktan ibaret değil, hayallerimizin ışığıdır.\" cümlesinde hangi sanat kullanılmıştır?", options: ["Benzetme", "İnsanlaştırma", "Atıf", "Teşbih"], correct: 1, skill: "Bilgileri ilişkilendirme", difficulty: 3, explain: "Güneş'e insan özelliği (ışık kaynağı olmak) verilmiştir: insanılaştırma." },

  // ============ FEN BİLİMLERİ (8 soru) ============
  { id: "q-fen-1", subject: "Fen Bilimleri", topic: "Madde ve Doğası", text: "Su 0°C'de buz olur. Bu olay hangi durum değişimidir?", options: ["Buharlaşma", "Erime", "Donma", "Yoğunlaşma"], correct: 2, skill: "Kural uygulama", difficulty: 1, explain: "Sıvıdan cisa geçişe donma denir." },
  { id: "q-fen-2", subject: "Fen Bilimleri", topic: "Madde ve Doğası", text: "Hangi madde manyetik alana etki göstermez?", options: ["Demir", "Nikel", "Bakır", "Kobalt"], correct: 2, skill: "Bilgiyi problem içinde yorumlama", difficulty: 2, explain: "Bakır manyetik olmayan bir metaldir." },
  { id: "q-fen-3", subject: "Fen Bilimleri", topic: "Canlıların Temel Bileşenleri", text: "Hücre zarının temel görevi nedir?", options: ["Enerji üretmek", "Hücreyi koruyup giriş-çıkışı kontrol etmek", "DNA depolamak", "Protein sentezlemek"], correct: 1, skill: "Bilgiyi problem içinde yorumlama", difficulty: 2, explain: "Hücre zarı seçici geçirgenlik gösterir, hücreyi çevreye karşı korur." },
  { id: "q-fen-4", subject: "Fen Bilimleri", topic: "DNA ve Kalıtım", text: "DNA'nın yapı taşı olan nükleotidlerin hangisi EŞLEŞMEZ?", options: ["Adenin - Timin", "Sitozin - Guanin", "Adenin - Sitozin", "Guanin - Sitozin"], correct: 2, skill: "Kural uygulama", difficulty: 2, explain: "A-T, C-G eşleşir. Adenin-Sitozin eşleşmez." },
  { id: "q-fen-5", subject: "Fen Bilimleri", topic: "Kuvvet ve Enerji", text: "10 N kuvvetle 5 m yol katedilir. Yapılan iş kaç Joule'dir?", options: ["2 J", "15 J", "50 J", "100 J"], correct: 2, skill: "Bilgiyi problem içinde yorumlama", difficulty: 2, explain: "İş = Kuvvet × Yol = 10 N × 5 m = 50 J" },
  { id: "q-fen-6", subject: "Fen Bilimleri", topic: "Dünya ve Evren", text: "Dünyanın güneş etrafında tam bir tur atması kaç gün sürer?", options: ["24 saat", "28 gün", "365 gün", "30 gün"], correct: 2, skill: "Bilgiyi problem içinde yorumlama", difficulty: 1, explain: "Dünyanın yörünge dönüş süresi yaklaşık 365.25 gündür." },
  { id: "q-fen-7", subject: "Fen Bilimleri", topic: "Elektrik ve Manyetizma", text: "Ampulün parlaklığını artırmak için devreye ne eklenmelidir?", options: ["Direnç", "Pil (gerginlik kaynağı)", "Anahtar", "İletken tel"], correct: 1, skill: "Bilgileri ilişkilendirme", difficulty: 2, explain: "Gerçinlik (pil) artarsa akım artar, ampul daha parlak yanar." },
  { id: "q-fen-8", subject: "Fen Bilimleri", topic: "Basit Makineler", text: "Kaldıraç hangi prensiple çalışır?", options: ["Kuvvet × Kuvvet kolu = Yük × Yük kolu", "Kuvvet + Kuvvet kolu = Yük + Yük kolu", "Kuvvet / Kuvvet kolu = Yük / Yük kolu", "Kuvvet - Kuvvet kolu = Yük - Yük kolu"], correct: 0, skill: "Kural uygulama", difficulty: 3, explain: "Kaldıraç denge denklemi: F₁ × d₁ = F₂ × d₂" },

  // ============ İNKILAP TARİHİ (6 soru) ============
  { id: "q-ink-1", subject: "İnkılap Tarihi", topic: "Türkiye Kurtuluş Savaşı", text: "Mudanya Mütarekesi ne zaman imzalanmıştır?", options: ["11 Ekim 1922", "24 Temmuz 1923", "29 Ekim 1923", "3 Mart 1924"], correct: 0, skill: "Bilgiyi problem içinde yorumlama", difficulty: 2, explain: "Mudanya Mütarekesi 11 Ekim 1922'de imzalanmıştır." },
  { id: "q-ink-2", subject: "İnkılap Tarihi", topic: "Türkiye Kurtuluş Savaşı", text: "Lozan Antlaşması hangi tarihte imzalanmıştır?", options: ["11 Ekim 1922", "24 Temmuz 1923", "29 Ekim 1923", "3 Mart 1924"], correct: 1, skill: "Bilgiyi problem içinde yorumlama", difficulty: 2, explain: "Lozan Antlaşması 24 Temmuz 1923'te imzalanmıştır." },
  { id: "q-ink-3", subject: "İnkılap Tarihi", topic: "Cumhuriyetin İlanı", text: "Türkiye Cumhuriyeti ne tarihte ilan edilmiştir?", options: ["23 Nisan 1920", "19 Mayıs 1919", "29 Ekim 1923", "3 Mart 1924"], correct: 2, skill: "Bilgiyi problem içinde yorumlama", difficulty: 1, explain: "Cumhuriyet 29 Ekim 1923'te ilan edilmiştir." },
  { id: "q-ink-4", subject: "İnkılap Tarihi", topic: "Atatürkçülük ve Çağdaşlaşan Türkiye", text: "Harf Devrimi ne zaman kabul edilmiştir?", options: ["1 Kasım 1928", "3 Kasım 1928", "1 Aralık 1928", "24 Kasım 1934"], correct: 0, skill: "Bilgiyi problem içinde yorumlama", difficulty: 2, explain: "Harf Devrimi 1 Kasım 1928'de kabul edilmiş, 1 Ocak 1929'dan itibaren yürürlüğe girmiştir." },
  { id: "q-ink-5", subject: "İnkılap Tarihi", topic: "Demokratikleşme Çabaları", text: "Türkiye'de çok partili hayata geçiş hangi yıl ve partiyle başlamıştır?", options: ["1945 - DP", "1946 - DP", "1950 - DP", "1960 - AP"], correct: 1, skill: "Bilgileri ilişkilendirme", difficulty: 3, explain: "Demokrat Parti 1946'da kurulmuş, çok partili hayata geçiş sağlanmıştır." },
  { id: "q-ink-6", subject: "İnkılap Tarihi", topic: "Atatürk Dönemi Türk Dış Politikası", text: "\"Yurtta sulh, cihanda sulh\" kimin söylemidir?", options: ["İsmet İnönü", "Mustafa Kemal Atatürk", "Celal Bayar", "Adnan Menderes"], correct: 1, skill: "Bilgiyi problem içinde yorumlama", difficulty: 1, explain: "Bu üslup Mustafa Kemal Atatürk'ün emeviyetidir." },

  // ============ DİN KÜLTÜRÜ (6 soru) ============
  { id: "q-din-1", subject: "Din Kültürü", topic: "Kur'an", text: "Kur'an kaç sureden oluşur?", options: ["99", "114", "120", "124"], correct: 1, skill: "Bilgiyi problem içinde yorumlama", difficulty: 1, explain: "Kur'an 114 sureden oluşur." },
  { id: "q-din-2", subject: "Din Kültürü", topic: "Kur'an", text: "Kur'an'ın en uzun suresi hangisidir?", options: ["Bakara", "Ali İmran", "Nisa", "En'am"], correct: 0, skill: "Bilgiyi problem içinde yorumlama", difficulty: 2, explain: "Bakara Suresi 286 ayetle en uzun suredir." },
  { id: "q-din-3", subject: "Din Kültürü", topic: "Hz. Muhammed", text: "Hz. Muhammed'in babasının adı nedir?", options: ["Abdullah", "Abdülmuttalib", "Ebu Talip", "Hamza"], correct: 0, skill: "Bilgiyi problem içinde yorumlama", difficulty: 2, explain: "Hz. Muhammed'in babası Abdullah'dır." },
  { id: "q-din-4", subject: "Din Kültürü", topic: "İbadetler", text: "Namaz farzı kaç vaktedir?", options: ["3", "4", "5", "6"], correct: 2, skill: "Kural uygulama", difficulty: 1, explain: "Günlük 5 vakit namaz farzdır." },
  { id: "q-din-5", subject: "Din Kültürü", topic: "Ahlak", text: "İslam'da en yüce ahlaki değer hangisidir?", options: ["Cömertlik", "Adalet", "Sabır", "Tövbekarlık"], correct: 1, skill: "Bilgileri ilişkilendirme", difficulty: 2, explain: "Adalet İslam ahlakının temel değeridir." },
  { id: "q-din-6", subject: "Din Kültürü", topic: "Müslüman Türkler", text: "Türkiye'de ilk Camiler hangi dönemde inşa edilmiştir?", options: ["Selçuklu", "Osmanlı", "Beylikler", "Türkiye Cumhuriyeti"], correct: 1, skill: "Bilgiyi problem içinde yorumlama", difficulty: 3, explain: "Osmanlı döneminde sistematik cami inşası başlamıştır." },

  // ============ İNGİLİZCE (6 soru) ============
  { id: "q-eng-1", subject: "İngilizce", topic: "Friendship", text: "Choose the correct form: \"She _____ my best friend.\"", options: ["am", "is", "are", "be"], correct: 1, skill: "Kural uygulama", difficulty: 1, explain: "She (3. tekil) için 'is' kullanılır." },
  { id: "q-eng-2", subject: "İngilizce", topic: "Teen Life", text: "Which sentence is correct? \"I _____ to school every day.\"", options: ["go", "goes", "going", "gone"], correct: 0, skill: "Kural uygulama", difficulty: 1, explain: "I (1. tekil) için fiil saf hali (go) kullanılır." },
  { id: "q-eng-3", subject: "İngilizce", topic: "In the Kitchen", text: "What is the English for \"Tencere\"?", options: ["Pan", "Pot", "Bowl", "Plate"], correct: 1, skill: "Bilgiyi problem içinde yorumlama", difficulty: 2, explain: "\"Tencere\" İngilizce \"pot\"tur." },
  { id: "q-eng-4", subject: "İngilizce", topic: "On the Phone", text: "Complete: \"Can I _____ to John, please?\"", options: ["speak", "talk", "say", "tell"], correct: 0, skill: "Kural uygulama", difficulty: 2, explain: "Telefonda 'speak to' kullanılır." },
  { id: "q-eng-5", subject: "İngilizce", topic: "The Internet", text: "\"www\" ne anlama gelir?", options: ["World Wide Web", "World Web Wide", "Wide World Web", "Web World Wide"], correct: 0, skill: "Bilgiyi problem içinde yorumlama", difficulty: 1, explain: "\"www\" = World Wide Web" },
  { id: "q-eng-6", subject: "İngilizce", topic: "Adventures", text: "Past form of \"go\" is _____.", options: ["goed", "went", "gone", "goes"], correct: 1, skill: "Kural uygulama", difficulty: 2, explain: "\"Go\" fiilinin geçmiş zamanı düzensizdir: went." },
];


/** İlerleme sayfası özet sayıları. */
export const errorSummary = { total: 52, resolved: 38, weekDelta: 7 };

/** Son 5 haftanın başarı yüzdesi (ilerleme grafiği). */
export const weeklyProgress = [
  { label: "1. Hafta", value: 58 },
  { label: "2. Hafta", value: 66 },
  { label: "3. Hafta", value: 70 },
  { label: "4. Hafta", value: 74 },
  { label: "5. Hafta", value: 79 },
];

/** Kankanın son gözlemleri (ana sayfa paneli). */
export const coachInsights = [
  {
    code: "H2" as const,
    title: "Yöntem seçiminde takılma",
    detail:
      "Son 10 Matematik sorusunda iki hatada çözüm yolunu seçme aşamasında durdun. Konuyu biliyorsun; soru tipini tanımayı çalışalım.",
  },
  {
    code: "H4" as const,
    title: "İşlem hatası azaldı",
    detail: "H4 hatan son 2 haftada %38'den %22'ye indi. Alt alta işlem alışkanlığı işe yarıyor, böyle devam.",
  },
  {
    code: "H3" as const,
    title: "Okuma ve modelleme",
    detail: "Fen sorularında verilenleri tabloya dökme adımını atlıyorsun; bu, iki soruda yanlış modele yol açtı.",
  },
];

export type Resource = {
  title: string;
  detail: string;
  tags: string[];
  href: string;
  external?: boolean;
  newTab?: boolean;
  links?: Array<{ label: string; url: string }>;
  tone: Tone;
};

/** Kaynaklar sayfası: resmî kaynaklar + kankanın hazırladığı özetler. */
export const resources: Resource[] = [
  {
    title: "Konu Özetleri",
    detail: "EBA'daki 8. sınıf konu anlatımı, örnek sorular ve çalışma materyalleri. Konuyu öğrenmek ve pekiştirmek için kullan.",
    tags: ["özet", "kısa"],
    href: "https://eba.gov.tr/misafir/dersler?duzey=Ortaokul&okulTuru=6&sinif=1",
    external: true,
    tone: "lavanta",
  },
  {
    title: "Konu Anlatım Kanalları",
    detail: "Konu anlatımı, soru çözümü ve sınav hazırlığı için YouTube kanalları.",
    tags: ["youtube", "konu anlatımı", "soru çözümü"],
    href: "",
    tone: "mavi",
    links: [
      { label: "Tonguç Akademi (genel)", url: "https://www.youtube.com/@tonguc8" },
      { label: "Partikül Matematik", url: "https://www.youtube.com/results?search_query=Partik%C3%BCl+Matematik+LGS+8.+s%C4%B1n%C4%B1f" },
      { label: "Haluk Seyit (Türkçe)", url: "https://www.youtube.com/results?search_query=Haluk+Seyit+LGS+T%C3%BCrk%C3%A7e" },
      { label: "Derslig (Fen)", url: "https://www.youtube.com/results?search_query=Derslig+8.+s%C4%B1n%C4%B1f+Fen+Bilimleri+LGS" },
      { label: "Sosyal Kale (İnkılap)", url: "https://www.youtube.com/results?search_query=Sosyal+Kale+LGS+%C4%B0nk%C4%B1lap+Tarihi" },
      { label: "Cebrail Hoca (Din)", url: "https://www.youtube.com/results?search_query=Cebrail+Hoca+LGS+Din+K%C3%BClt%C3%BCr%C3%BC" },
      { label: "Sercan İğrek (İngilizce)", url: "https://www.youtube.com/@sercanigrek" },
      { label: "Hocalara Geldik (genel)", url: "https://www.youtube.com/results?search_query=Hocalara+Geldik+8.+s%C4%B1n%C4%B1f+LGS" },
    ],
  },
  {
    title: "MEB Örnek Sorular",
    detail: "Millî Eğitim Bakanlığı'nın yayımladığı 8. sınıf örnek sorular ve çalışma fasikülleri.",
    tags: ["resmî", "soru"],
    href: "https://odsgm.meb.gov.tr/www/ornek-sorular/icerik/1011",
    external: true,
    tone: "mint",
  },
  {
    title: "EBA Ders Videoları",
    detail: "Eğitim Bilişim Ağı'ndaki konu anlatım videoları; kankanın önerdiği sıralamayla izlemen yeterli.",
    tags: ["video", "resmî"],
    href: "https://www.eba.gov.tr",
    external: true,
    tone: "pembe",
  },
  {
    title: "Sınav Kaygısı Rehberi",
    detail: "Sınav stresi herkeste aynı olmayabilir. Birkaç işaret fark etmek, kendine kızmak yerine destek bulmana yardım eder.",
    tags: ["rehber", "iyi hâl"],
    href: "/lgs-kaygi-ve-bas-etme.html",
    newTab: true,
    tone: "limon",
  },
];

export type MemoryPair = {
  id: string;
  subject: string;
  /** Kartın bir yüzü: kavram/kısaltma. */
  term: string;
  /** Kartın diğer yüzü: karşılığı/tanımı. */
  definition: string;
};

/**
 * Hafıza Kartları oyunu — plan §38.1: 6 çift = 12 kart.
 * Her turda kavram ↔ karşılığı eşleştirilir; yanlış eşleşmede kartlar geri kapanır.
 * Not: Bu içerik AI üretimi değil, müfredat bilgisidir (telifli metin içermez).
 */
export const memoryPairs: MemoryPair[] = [
  {
    id: "uslu-carpma",
    subject: "Matematik",
    term: "aᵐ · aⁿ",
    definition: "Tabanlar aynıysa üsler toplanır: aᵐ⁺ⁿ",
  },
  {
    id: "karekok-sadelestirme",
    subject: "Matematik",
    term: "√72",
    definition: "6√2 (tam kare çarpan kök dışına çıkar)",
  },
  {
    id: "tam-kare-acilim",
    subject: "Matematik",
    term: "(a + b)²",
    definition: "a² + 2ab + b²",
  },
  {
    id: "kalitim-birimi",
    subject: "Fen Bilimleri",
    term: "Kalıtım birimi",
    definition: "Gen",
  },
  {
    id: "basinc-birimi",
    subject: "Fen Bilimleri",
    term: "Basınç birimi",
    definition: "Pascal (Pa)",
  },
  {
    id: "devrik-cumle",
    subject: "Türkçe",
    term: "Devrik cümle",
    definition: "Yüklemi sonda olmayan cümle",
  },
];

/** Öğrencinin yanlış cevaptan sonra seçebileceği nedenler. */
export const wrongReasons = [
  "Soruyu anlamadım",
  "Yöntemi bilmiyordum",
  "İşlem hatası yaptım",
  "Dikkatim dağıldı",
] as const;
