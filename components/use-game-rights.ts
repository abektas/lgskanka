"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { dailyGameMinutes, gameEconomy } from "../data/nav";

/**
 * Günlük oyun hakkı ve süresi — plan §18/§38.3'ün yerel (localStorage) uygulaması.
 *
 * Kurallar:
 *  - Günde en fazla `gameEconomy.dailySessionLimit` tur (her tur 1 hak).
 *  - Günde en fazla `gameEconomy.dailyMinuteLimit` dakika.
 *  - Süre hakkı XP eşiğinden gelir (`dailyGameMinutes`); eşik altındaki öğrenciye oyun açılmaz.
 *  - Oyun XP kazandırmaz; yalnızca hak ve süre harcar.
 *
 * Henüz sunucu yok: kayıt tarayıcıda tutulur. Plan Faz 14'te (XP/oyun session tabloları)
 * bu kayıt veritabanına taşınacak; arayüz sözleşmesi (rights/remainingSeconds/blockedReason)
 * aynı kalacak.
 */

export type GameBlockedReason = "rights" | "time" | "xp" | null;

type DayRecord = {
  /** YYYY-MM-DD — gün değişince kayıt sıfırlanır. */
  day: string;
  /** Bugün başlatılan tur sayısı. */
  sessions: number;
  /** Bugün oyunda geçirilen saniye. */
  seconds: number;
};

const STORAGE_KEY = "lgs-ai-coach-game-session";

function todayKey(date = new Date()): string {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

/** Demo verisindeki `gameRights` değerini güne başlangıç olarak kabul eder. */
function seedRecord(seedRights: number): DayRecord {
  const used = Math.max(0, gameEconomy.dailySessionLimit - Math.max(0, seedRights));
  return { day: todayKey(), sessions: used, seconds: 0 };
}

function isSameRecord(value: unknown, day: string): value is DayRecord {
  if (!value || typeof value !== "object") return false;
  const record = value as Partial<DayRecord>;
  return (
    record.day === day &&
    typeof record.sessions === "number" &&
    Number.isFinite(record.sessions) &&
    typeof record.seconds === "number" &&
    Number.isFinite(record.seconds)
  );
}

export type GameRights = {
  /** localStorage okundu mu? (ilk boyamada yanlış sayı göstermemek için) */
  ready: boolean;
  /** Bugün kalan tur hakkı. */
  rights: number;
  /** XP'den gelen günlük süre hakkı (dakika). */
  minutesAllowance: number;
  /** Bugün kalan oyun süresi (saniye). */
  remainingSeconds: number;
  /** Oyun neden açılamıyor? `null` ise oynanabilir. */
  blockedReason: GameBlockedReason;
  /** Yeni tur: 1 hak harcar. */
  startRound: () => void;
  /** Tur bitince/çıkışta oynanan süreyi günlük kullanıma ekler. */
  recordRound: (seconds: number) => void;
};

export function useGameRights(xp: number, seedRights: number): GameRights {
  const [record, setRecord] = useState<DayRecord>(() => seedRecord(seedRights));
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const day = todayKey();
    let next = seedRecord(seedRights);
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed: unknown = JSON.parse(raw);
        if (isSameRecord(parsed, day)) {
          next = {
            day,
            sessions: Math.min(gameEconomy.dailySessionLimit, Math.max(0, parsed.sessions)),
            seconds: Math.max(0, parsed.seconds),
          };
        }
      }
    } catch {
      /* bozuk kayıt: güne demo değerleriyle başla */
    }
    setRecord(next);
    setReady(true);
  }, [seedRights]);

  useEffect(() => {
    if (!ready) return;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(record));
    } catch {
      /* depolama kapalıysa yalnızca bellekte tut */
    }
  }, [ready, record]);

  /** Gün değiştiyse kaydı bugüne taşıyan ortak yardımcı. */
  const withToday = useCallback(
    (prev: DayRecord): DayRecord => (prev.day === todayKey() ? prev : seedRecord(seedRights)),
    [seedRights],
  );

  const startRound = useCallback(() => {
    setRecord((prev) => {
      const base = withToday(prev);
      return { ...base, sessions: Math.min(gameEconomy.dailySessionLimit, base.sessions + 1) };
    });
  }, [withToday]);

  const recordRound = useCallback(
    (seconds: number) => {
      const spent = Math.max(0, Math.round(seconds));
      if (spent === 0) return;
      setRecord((prev) => {
        const base = withToday(prev);
        return { ...base, seconds: base.seconds + spent };
      });
    },
    [withToday],
  );

  const minutesAllowance = useMemo(() => dailyGameMinutes(xp), [xp]);

  const remainingSeconds = useMemo(() => {
    const allowance = minutesAllowance * 60;
    return Math.max(0, allowance - record.seconds);
  }, [minutesAllowance, record.seconds]);

  const rights = Math.max(0, gameEconomy.dailySessionLimit - record.sessions);

  const blockedReason: GameBlockedReason =
    minutesAllowance === 0 ? "xp" : rights <= 0 ? "rights" : remainingSeconds <= 0 ? "time" : null;

  return {
    ready,
    rights,
    minutesAllowance,
    remainingSeconds,
    blockedReason,
    startRound,
    recordRound,
  };
}
