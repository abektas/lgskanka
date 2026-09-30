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
    href: "/dersler",
    minutes: 12,
  },
  {
    id: "mini-test",
    icon: "📝",
    title: "Haftalık Mini Test",
    detail: "20 soru · karışık konular",
    xp: 20,
    href: "/sinavlar",
    minutes: 25,
  },
  {
    id: "ai-koc",
    icon: "🤖",
    title: "AI Koç ile hata analizi",
    detail: "Son 3 yanlışını birlikte çözelim",
    xp: 5,
    href: "/ai-koc",
    minutes: 8,
  },
];

export type ErrorType = {
  code: "H1" | "H2" | "H3" | "H4" | "H5" | "H6" | "H7";
  name: string;
  color: string;
  share: number;
  definition: string;
  advice: string;
};

/** H1–H7 hata taksonomisi: koçun teşhis ettiği hata türleri. */
export const errorTypes: ErrorType[] = [
  {
    code: "H1",
    name: "Kavram eksikliği",
    color: "#FF7BAC",
    share: 18,
    definition: "Konu bilgisi eksik ya da yanlış öğrenilmiş.",
    advice: "Önce konu özetini oku, sonra aynı kazanımdan 5 kolay soru çöz.",
  },
  {
    code: "H2",
    name: "Yöntem / strateji",
    color: "#FF9A5A",
    share: 22,
    definition: "Konuyu biliyorsun ama çözüm yolunu seçemiyorsun.",
    advice: "Soru tipini tanımla: verilen ne, istenen ne? Adımları yaz.",
  },
  {
    code: "H3",
    name: "Okuma / modelleme",
    color: "#3D8BFF",
    share: 28,
    definition: "Metni veya görseli yanlış yorumlayıp model kuramama.",
    advice: "Soruyu kendi cümlenle yeniden yaz, verileri tabloya dök.",
  },
  {
    code: "H4",
    name: "İşlem hatası",
    color: "#16B98A",
    share: 32,
    definition: "Yol doğru, hesaplama kayıyor.",
    advice: "İşlemi iki kez kontrol et; kâğıtta alt alta yaz.",
  },
  {
    code: "H5",
    name: "Gereksiz bilgi",
    color: "#9A65F5",
    share: 12,
    definition: "Sorudaki fazladan bilgiye takılmak.",
    advice: "Önce isteneni belirle, sonra gereken veriyi işaretle.",
  },
  {
    code: "H6",
    name: "İlişkilendirme",
    color: "#F5B93E",
    share: 24,
    definition: "Bilgileri birbiriyle bağlayamama.",
    advice: "Birden çok konu geçen sorularda ara adımları yaz.",
  },
  {
    code: "H7",
    name: "Dikkat",
    color: "#FF6B6B",
    share: 15,
    definition: "Hızlı okuma veya acele kaynaklı hata.",
    advice: "25 dakikada 5 soru; son 2 dakikada sadece kontrol.",
  },
];

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
  { icon: "⏱️", name: "Hız Oyunu", detail: "30 saniyede kaç soru?", minutes: 3 },
];

/** 5 haftalık deneme programı — haftalık deneme sınavı planı. */
export const examPlan = [
  { week: "1. Hafta", subject: "Sözel Bölüm", date: "6 Ekim", status: "done" as const },
  { week: "2. Hafta", subject: "Sayısal Bölüm", date: "13 Ekim", status: "done" as const },
  { week: "3. Hafta", subject: "Genel Deneme", date: "20 Ekim", status: "active" as const },
  { week: "4. Hafta", subject: "Sözel Bölüm", date: "27 Ekim", status: "upcoming" as const },
  { week: "5. Hafta", subject: "Genel Deneme", date: "3 Kasım", status: "upcoming" as const },
];

export type Question = {
  id: string;
  subject: string;
  topic: string;
  text: string;
  options: string[];
  correct: number;
  skill: string;
  difficulty: 1 | 2 | 3;
  /** Her seçenek için koçun ön teşhisi (doğru cevap dâhil). */
  explain: string;
};

export const questionBank: Question[] = [
  {
    id: "q-uslu-1",
    subject: "Matematik",
    topic: "Üslü İfadeler",
    text: "Aşağıdakilerden hangisi 2³ · 2⁵ işleminin sonucuna eşittir?",
    options: ["2⁸", "2¹⁰", "2¹²", "2¹⁵"],
    correct: 0,
    skill: "Bilgiyi problem içinde yorumlama",
    difficulty: 2,
    explain: "Aynı tabanlı üsler çarpılırken üsler toplanır: 2³ · 2⁵ = 2³⁺⁵ = 2⁸",
  },
  {
    id: "q-uslu-2",
    subject: "Matematik",
    topic: "Üslü İfadeler",
    text: "(3²)³ ifadesinin eşiti aşağıdakilerden hangisidir?",
    options: ["3⁵", "3⁶", "3⁹", "6³"],
    correct: 1,
    skill: "Kural uygulama",
    difficulty: 2,
    explain: "Üssün üssü alınırken üsler çarpılır: (3²)³ = 3²ˣ³ = 3⁶",
  },
  {
    id: "q-kok-1",
    subject: "Matematik",
    topic: "Kareköklü İfadeler",
    text: "√72 sayısı aşağıdakilerden hangisine eşittir?",
    options: ["6√2", "8√2", "4√3", "2√18"],
    correct: 0,
    skill: "Bilgiyi problem içinde yorumlama",
    difficulty: 3,
    explain: "72 = 36 · 2 olduğundan √72 = √36 · √2 = 6√2",
  },
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

/** Koçun son gözlemleri (AI Koç sayfası + ana sayfa paneli). */
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
  tone: Tone;
};

/** Kaynaklar sayfası: resmî kaynaklar + koçun hazırladığı özetler. */
export const resources: Resource[] = [
  {
    title: "Konu Özetleri",
    detail: "Koçun senin hatalarına göre hazırladığı 5 dakikalık özetler; her özet bittiğinde 3 soruyla pekiştiriyorsun.",
    tags: ["özet", "kısa"],
    href: "/dersler",
    tone: "lavanta",
  },
  {
    title: "Hata Analizi Kütüphanesi",
    detail: "H1–H7 hata türlerinin ne anlama geldiğini ve her biri için çözüm adımlarını anlatan rehber.",
    tags: ["hata analizi", "rehber"],
    href: "/ilerleme",
    tone: "mavi",
  },
  {
    title: "Deneme Sınavı Arşivi",
    detail: "Haftalık denemeler, cevap anahtarı ve soru bazında analiz. Yanlışların otomatik olarak hata türüne ayrılır.",
    tags: ["deneme", "analiz"],
    href: "/sinavlar",
    tone: "seftali",
  },
  {
    title: "MEB Örnek Sorular",
    detail: "Millî Eğitim Bakanlığı'nın yayımladığı 8. sınıf örnek sorular ve çalışma fasikülleri.",
    tags: ["resmî", "soru"],
    href: "https://www.meb.gov.tr",
    external: true,
    tone: "mint",
  },
  {
    title: "EBA Ders Videoları",
    detail: "Eğitim Bilişim Ağı'ndaki konu anlatım videoları; koçun önerdiği sıralamayla izlemen yeterli.",
    tags: ["video", "resmî"],
    href: "https://www.eba.gov.tr",
    external: true,
    tone: "pembe",
  },
  {
    title: "Sınav Kaygısı Rehberi",
    detail: "Sınav öncesi nefes, uyku ve ders programı düzeni için 10 maddelik sade bir kontrol listesi.",
    tags: ["rehber", "iyi hâl"],
    href: "/ai-koc",
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
