/**
 * Haftalık test geçmişi — kalıcı kayıt (localStorage).
 *
 * Her test bitişinde özet + kategori dökümü + zayıf üniteler kaydedilir.
 * Rapor sayfası ve /calis özeti bu kayıtları okur.
 */

import type { TestCategory } from "./weekly-test";

export const WEEKLY_TEST_HISTORY_KEY = "lgs_weekly_test_history";

/** Bir haftalık test kaydı. */
export interface WeeklyTestRecord {
  /** ISO tarih (testin bittiği an) */
  date: string;
  /** Toplam soru sayısı */
  total: number;
  /** Doğru sayısı */
  correct: number;
  /** Yanlış sayısı */
  wrong: number;
  /** Boş/belirsiz sayısı */
  blank: number;
  /** Kategori bazlı döküm */
  byCategory: Record<TestCategory, { total: number; correct: number }>;
  /** Testteki zayıf üniteler (konu + doğruluk) */
  weakUnits: Array<{
    subject: string;
    unit: number | null;
    unitName: string | null;
    accuracy: number;
    level: string;
    due: boolean;
  }>;
  /** Testteki soruların ID'leri (tekrar sormamak için) */
  questionIds: string[];
}

/** Geçmiş kayıtlarını okur (en yenisi sonda). */
export function loadWeeklyTestHistory(): WeeklyTestRecord[] {
  try {
    const raw = localStorage.getItem(WEEKLY_TEST_HISTORY_KEY);
    const list = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

/** Yeni bir test kaydını sona ekler (en fazla 52 kayıt = 1 yıl tutulur). */
export function saveWeeklyTestRecord(record: WeeklyTestRecord): WeeklyTestRecord[] {
  const history = loadWeeklyTestHistory();
  history.push(record);
  const trimmed = history.slice(-52);
  try {
    localStorage.setItem(WEEKLY_TEST_HISTORY_KEY, JSON.stringify(trimmed));
  } catch {
    // Depolama hatası sessizce atlanır
  }
  return trimmed;
}

/** Son kaydı döndürür (yoksa null). */
export function latestWeeklyTest(): WeeklyTestRecord | null {
  const history = loadWeeklyTestHistory();
  return history.length > 0 ? history[history.length - 1] : null;
}

/** Son N kaydı döndürür (en yenisi önce). */
export function recentWeeklyTests(n: number = 5): WeeklyTestRecord[] {
  return loadWeeklyTestHistory().slice(-n).reverse();
}

/** Geçmiş kayıtlardan ortalama başarı oranı (%). */
export function weeklyTestAverage(n: number = 5): number {
  const recent = recentWeeklyTests(n);
  if (recent.length === 0) return 0;
  const totalCorrect = recent.reduce((sum, r) => sum + r.correct, 0);
  const totalQuestions = recent.reduce((sum, r) => sum + r.total, 0);
  return totalQuestions > 0 ? Math.round((totalCorrect / totalQuestions) * 100) : 0;
}

/** Bir önceki testle karşılaştırarak değişim (+/- puan). */
export function weeklyTestDelta(): number {
  const recent = recentWeeklyTests(2);
  if (recent.length < 2) return 0;
  const [latest, prev] = recent;
  const latestPct = latest.total > 0 ? (latest.correct / latest.total) * 100 : 0;
  const prevPct = prev.total > 0 ? (prev.correct / prev.total) * 100 : 0;
  return Math.round(latestPct - prevPct);
}