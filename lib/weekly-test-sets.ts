/**
 * Haftalık test soru setleri — hafta başına kalıcı kayıt (localStorage).
 *
 * Neden gerekli: test soruları havuzdan her açılışta yeniden seçildiği için
 * "önceki haftanın testi" diye bir şey yoktu. Öğrenci cumartesi çözemediyse
 * o haftanın testi kayboluyordu. Artık bir hafta ilk kez açıldığında soru seti
 * hafta anahtarıyla saklanır; sonradan açıldığında aynı sorular gelir.
 */

import type { TestItem } from "./weekly-test";

export const WEEKLY_TEST_SETS_KEY = "lgs_weekly_test_sets";

/** Bir haftanın dondurulmuş testi. */
export interface WeeklyTestSet {
  /** Haftanın cumartesisi — YYYY-MM-DD */
  weekKey: string;
  /** Setin oluşturulduğu an (ISO) */
  createdAt: string;
  items: TestItem[];
}

/** En fazla 16 hafta tutulur (4 ay). */
const MAX_SETS = 16;

type Store = Record<string, WeeklyTestSet>;

function readStore(): Store {
  try {
    const raw = localStorage.getItem(WEEKLY_TEST_SETS_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === "object" ? (parsed as Store) : {};
  } catch {
    return {};
  }
}

function writeStore(store: Store): void {
  try {
    const keys = Object.keys(store).sort();
    const keep = keys.slice(-MAX_SETS);
    const trimmed: Store = {};
    for (const key of keep) trimmed[key] = store[key];
    window.localStorage.setItem(WEEKLY_TEST_SETS_KEY, JSON.stringify(trimmed));
  } catch {
    /* depolama kapalıysa yoksay */
  }
}

/** Haftanın dondurulmuş testini döndürür (yoksa null). */
export function getWeeklyTestSet(weekKey: string): WeeklyTestSet | null {
  const set = readStore()[weekKey];
  return set && Array.isArray(set.items) && set.items.length > 0 ? set : null;
}

/** Haftanın testini dondurur (varsa dokunmaz). */
export function saveWeeklyTestSet(weekKey: string, items: TestItem[]): WeeklyTestSet {
  const store = readStore();
  const existing = store[weekKey];
  if (existing && Array.isArray(existing.items) && existing.items.length > 0) return existing;
  const set: WeeklyTestSet = { weekKey, createdAt: new Date().toISOString(), items };
  store[weekKey] = set;
  writeStore(store);
  return set;
}

/** Kayıtlı hafta anahtarları. */
export function storedWeeklyTestWeekKeys(): string[] {
  return Object.keys(readStore()).sort();
}
