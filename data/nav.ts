import type { IconName } from "../components/icons";

export type NavItem = {
  href: string;
  label: string;
  icon: IconName;
  /** Mobil alt menüde gösterilsin mi (en fazla 5 öğe). */
  mobile?: boolean;
};

export const navItems: NavItem[] = [
  { href: "/", label: "Ana Sayfa", icon: "home", mobile: true },
  { href: "/calis", label: "Çalış", icon: "target", mobile: true },
  { href: "/ai-koc", label: "AI Koç", icon: "robot", mobile: true },
  { href: "/dersler", label: "Dersler", icon: "book" },
  { href: "/sinavlar", label: "Sınavlar", icon: "trophy" },
  { href: "/kaynaklar", label: "Kaynaklar", icon: "compass" },
  { href: "/oduller", label: "Ödüller", icon: "star" },
  { href: "/ilerleme", label: "İlerleme", icon: "chart", mobile: true },
  { href: "/profil", label: "Profil", icon: "user", mobile: true },
];

/** Öğrencinin anlık durumu (demo veri: sonraki adımda API'den gelecek). */
export const learner = {
  streakDays: 4,
  xp: 245,
  level: 4,
  levelXp: 145,
  levelTarget: 320,
  badgeCount: 8,
  gameRights: 2,
  roomItems: 3,
  solvedThisWeek: 42,
  weeklyGoal: 60,
  totalSolved: 286,
};

/** Haftalık test dağılımı — plan §12. */
export const weeklyTestPlan = [
  { subject: "Matematik", count: 10 },
  { subject: "Türkçe", count: 8 },
  { subject: "Fen Bilimleri", count: 6 },
  { subject: "İngilizce", count: 2 },
  { subject: "T.C. İnkılap Tarihi", count: 2 },
  { subject: "Din Kültürü", count: 2 },
];

/** XP kuralları — plan §18 (XP farming'i engellemek için sabit ve denetlenebilir). */
export const xpRules = [
  { action: "10 soru çözme", xp: 10 },
  { action: "Hata analizi yapma", xp: 5 },
  { action: "Sesli/yazılı açıklama ekleme", xp: 5 },
  { action: "Konu tekrarı", xp: 15 },
  { action: "Video + mini test", xp: 15 },
  { action: "Günlük hedefi tamamlama", xp: 20 },
  { action: "Haftalık test", xp: 30 },
  { action: "5 haftalık deneme", xp: 50 },
  { action: "Zayıf konuda gelişim", xp: 25 },
];

/**
 * Oyun ekonomisi — plan §18/§38.3.
 * Temel kural: oyun XP kazandırmaz; XP ile kazanılmış hak ve süreyi harcar (XP farming engeli).
 */
export const gameEconomy = {
  /** Günlük en fazla oyun oturumu. */
  dailySessionLimit: 2,
  /** Günlük en fazla oyun süresi (dakika). */
  dailyMinuteLimit: 10,
  /** XP eşiği → günlük oyun süresi. Eşiğin altındaki öğrenciye oyun açılmaz. */
  tiers: [
    { xp: 20, minutes: 2, label: "20 XP → 2 dakika" },
    { xp: 50, minutes: 5, label: "50 XP → 5 dakika" },
    { xp: 100, minutes: 10, label: "100 XP → 10 dakika" },
  ],
  /** Plan §18'deki seviye kilidi notu. */
  unlockNote: "100 XP → bir sonraki seviyede yeni oyun açılır",
} as const;

/**
 * XP'ye karşılık gelen günlük oyun süresi (dakika).
 * Eşikler kümülatif değil, aşılan en yüksek eşik geçerlidir; üst sınır `dailyMinuteLimit`.
 */
export function dailyGameMinutes(xp: number): number {
  let minutes = 0;
  for (const tier of gameEconomy.tiers) {
    if (xp >= tier.xp) minutes = tier.minutes;
  }
  return Math.min(minutes, gameEconomy.dailyMinuteLimit);
}

/** Mastery bantları — plan §45. */
export const masteryBands = [
  { range: "0–39", label: "Zayıf", tone: "pembe" as const, advice: "Konu tekrarı + kolay sorularla temel kur." },
  { range: "40–59", label: "Gelişiyor", tone: "seftali" as const, advice: "Karışık 10 soru, her yanlışta hata analizi." },
  { range: "60–79", label: "Yeterli", tone: "limon" as const, advice: "Yeni nesil sorularla zorluk artır." },
  { range: "80–100", label: "Güçlü", tone: "mint" as const, advice: "Tekrar aralığını uzat, süre tut." },
];
