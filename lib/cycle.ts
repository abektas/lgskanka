/**
 * Çalışma döngüsü — kayıt tarihinden başlayan 4 haftalık ritim.
 *
 * Kural (kullanıcı tarafından belirlendi):
 * - Hafta içi (Pzt–Cum): Günlük Alıştırmalar
 * - Hafta sonu (Cmt–Paz): sınav günü — 1., 2. ve 3. hafta → Haftalık Test,
 *   4. hafta → Aylık Deneme
 * - Cumartesi ve pazar aynı teste girilebilir (esnek hafta sonu).
 *
 * Döngü öğrencinin sisteme kaydolduğu günden başlar. Kayıt tarihi
 * localStorage'da tutulur (`lgs_enrollment_date`).
 */

export type DayType = "gunluk" | "haftalik" | "aylik" | "dinlenme";

export const ENROLLMENT_STORAGE_KEY = "lgs_enrollment_date";

/** Kayıt tarihi değiştiğinde yayınlanan olay (UI'lar yeniden hesaplasın). */
export const ENROLLMENT_CHANGED_EVENT = "lgs:enrollment-changed";

/** Döngüde haftalık test olan haftalar (1-3), 4. hafta aylık deneme. */
export const WEEKLY_TEST_WEEKS = [1, 2, 3] as const;
export const MONTHLY_EXAM_WEEK = 4;

/** Toplam döngü uzunluğu (hafta). */
export const CYCLE_WEEKS = 4;

export interface CycleState {
  /** Bugünün gün tipi */
  dayType: DayType;
  /** Döngüdeki hafta (1-4) */
  cycleWeek: number;
  /** Döngünün kaçıncı turu (1'den başlar) */
  cycleNumber: number;
  /** Kayıt tarihinden bugüne geçen gün */
  daysSinceEnrollment: number;
  /** Bu haftanın cumartesi günü (ISO) */
  saturdayOfThisWeek: string;
  /** Bu haftanın pazar günü (ISO) */
  sundayOfThisWeek: string;
  /** Bugün hafta sonu mu (cumartesi veya pazar) */
  isWeekend: boolean;
  /** Bugün cumartesi mi */
  isSaturday: boolean;
  /** Döngüdeki haftanın cumartesisi (ISO) */
  cycleSaturday: string;
  /** Bu hafta sonunun sınavı hangi test? */
  weekendTest: "haftalik" | "aylik";
}

/** Kayıt tarihini okur; yoksa bugünü döndürür ve kaydeder. */
export function getEnrollmentDate(now: Date = new Date()): Date {
  if (typeof window === "undefined") return now;
  try {
    const raw = window.localStorage.getItem(ENROLLMENT_STORAGE_KEY);
    if (raw) {
      const parsed = new Date(raw);
      if (!Number.isNaN(parsed.getTime())) return parsed;
    }
    // İlk açılış = kayıt anı
    window.localStorage.setItem(ENROLLMENT_STORAGE_KEY, now.toISOString());
  } catch {
    /* depolama kapalıysa bugünü kullan */
  }
  return now;
}

/** Kayıt tarihini dışarıdan ayarlar (profil düzenleme / demo). */
export function setEnrollmentDate(date: Date): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(ENROLLMENT_STORAGE_KEY, date.toISOString());
  } catch {
    /* depolama kapalıysa yoksay */
  }
  // Açık UI'ların yeniden hesaplaması için bildir
  window.dispatchEvent(new CustomEvent(ENROLLMENT_CHANGED_EVENT));
}

/** Verilen tarihin içinde bulunduğu haftanın pazartesisi (00:00). */
function startOfWeek(date: Date): Date {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  const day = d.getDay(); // 0=Pazar ... 6=Cumartesi
  const diff = day === 0 ? -6 : 1 - day; // pazartesiye normalize et
  d.setDate(d.getDate() + diff);
  return d;
}

/** Verilen tarihin içinde bulunduğu haftanın cumartesisi (00:00). */
function saturdayOfWeek(date: Date): Date {
  const monday = startOfWeek(date);
  const sat = new Date(monday);
  sat.setDate(sat.getDate() + 5);
  return sat;
}

/** İki tarihin arasındaki hafta farkı (pazartesi bazında). */
function diffWeeks(a: Date, b: Date): number {
  return Math.round((startOfWeek(b).getTime() - startOfWeek(a).getTime()) / (7 * 24 * 60 * 60 * 1000));
}

/**
 * Bugünün döngü durumunu hesaplar.
 * Döngü kayıt tarihinin içinde bulunduğu haftada başlar (1. hafta).
 */
export function computeCycleState(now: Date = new Date(), enrollment?: Date): CycleState {
  const enrolled = enrollment ?? getEnrollmentDate(now);

  const day = now.getDay(); // 0=Pazar ... 6=Cumartesi
  const isSaturday = day === 6;
  const isSunday = day === 0;
  const isWeekend = isSaturday || isSunday;

  // Kayıt haftasından itibaren geçen hafta sayısı
  const weeksPassed = Math.max(0, diffWeeks(enrolled, now));
  const cycleWeek = (weeksPassed % CYCLE_WEEKS) + 1;
  const cycleNumber = Math.floor(weeksPassed / CYCLE_WEEKS) + 1;

  // Bu hafta sonunun sınavı: 4. hafta aylık deneme, diğerleri haftalık test
  const weekendTest: "haftalik" | "aylik" =
    cycleWeek === MONTHLY_EXAM_WEEK ? "aylik" : "haftalik";

  let dayType: DayType;
  if (isSaturday) {
    dayType = weekendTest;
  } else if (isSunday && weekendTest === "aylik") {
    // Aylık deneme pazar günü de devam eder (90 soru için 2 gün)
    dayType = "aylik";
  } else {
    dayType = "gunluk";
  }

  const thisSaturday = saturdayOfWeek(now);
  const thisSunday = new Date(thisSaturday);
  thisSunday.setDate(thisSunday.getDate() + 1);

  // Döngünün o cumartesisi: geriye doğru cycleWeek-1 hafta
  const cycleSaturday = new Date(thisSaturday);
  cycleSaturday.setDate(cycleSaturday.getDate() - (cycleWeek - 1) * 7);

  return {
    dayType,
    cycleWeek,
    cycleNumber,
    daysSinceEnrollment: Math.max(
      0,
      Math.floor(
        (new Date(now).setHours(0, 0, 0, 0) - new Date(enrolled).setHours(0, 0, 0, 0)) / 86400000
      )
    ),
    saturdayOfThisWeek: thisSaturday.toISOString(),
    sundayOfThisWeek: thisSunday.toISOString(),
    isWeekend,
    isSaturday,
    cycleSaturday: cycleSaturday.toISOString(),
    weekendTest,
  };
}

/** Gün tipine göre kullanıcıya gösterilecek açıklama. */
export function dayTypeLabel(dayType: DayType): string {
  switch (dayType) {
    case "gunluk":
      return "Günlük çalışma günü";
    case "haftalik":
      return "Haftalık test günü";
    case "aylik":
      return "Aylık deneme günü";
    case "dinlenme":
      return "Dinlenme günü";
  }
}

/** Gün tipine göre hedef sayfa yolu. */
export function dayTypeHref(dayType: DayType): string | null {
  switch (dayType) {
    case "haftalik":
      return "/haftalik-test";
    case "aylik":
      return "/aylik-denemeler";
    default:
      return null;
  }
}

/** Döngü özeti — UI'da gösterilecek açıklama. */
export function cycleSummary(state: CycleState, pageVariant?: "haftalik" | "aylik"): string {
  const { cycleWeek, cycleNumber, weekendTest, isSaturday } = state;
  const weekText = `${cycleWeek}. hafta`;
  const testName = pageVariant === "aylik" ? "aylık deneme" : pageVariant === "haftalik" ? "haftalık test" : (weekendTest === "aylik" ? "aylık deneme" : "haftalık test");

  if (state.isWeekend) {
    if (weekendTest === "aylik") {
      return `${weekText} (${cycleNumber}. döngü) · Bugün aylık deneme günü. Cumartesi ve pazar aynı denemeye girebilirsin.`;
    }
    return `${weekText} (${cycleNumber}. döngü) · Bugün haftalık test günü (cumartesi). ${isSaturday ? "Hadi başla!" : "Yarın cumartesi — haftalık test çözülebilir."}`;
  }
  if (cycleWeek === 3) {
    return `${weekText} (${cycleNumber}. döngü) · Hafta içi günlük çalışma. Hafta sonu haftalık test, sonraki hafta sonu aylık deneme var.`;
  }
  if (cycleWeek === MONTHLY_EXAM_WEEK) {
    return `${weekText} (${cycleNumber}. döngü) · Hafta içi günlük çalışma. Hafta sonu aylık deneme var — önceki 3 haftalık testlerde tespit edilen eksikler buraya aktarıldı.`;
  }
  return `${weekText} (${cycleNumber}. döngü) · Hafta içi günlük çalışma. Hafta sonu ${testName} var.`;
}
