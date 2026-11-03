import { useEffect, useState } from "react";
import { loadAnswerRecords } from "./error-reason";

export interface LearnerStats {
  /** Toplam XP — doğru başına 2 XP (/calis günlük özetiyle aynı kural). */
  xp: number;
  /** Kesintisiz çalışma serisi (bugün veya dün biten). */
  streakDays: number;
  level: number;
  /** Mevcut seviyeye giren XP. */
  levelXp: number;
  /** Bir sonraki seviye için gereken XP farkı. */
  levelTarget: number;
}

/** Seviye eşikleri — kümülatif XP (plan §18: sabit ve denetlenebilir). */
const LEVEL_THRESHOLDS = [0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200];

/** Cevap kayıtlarından gerçek öğrenci istatistikleri. */
export function computeLearnerStats(): LearnerStats {
  const records = loadAnswerRecords();
  const xp = records.filter((r) => r.correct).length * 2;

  // Çalışma serisi: bugünden (bugün yoksa dünden) geriye doğru kesintisiz günler
  const days = new Set(records.map((r) => String(r.createdAt).slice(0, 10)));
  const cursor = new Date();
  if (!days.has(cursor.toISOString().slice(0, 10))) {
    cursor.setDate(cursor.getDate() - 1);
  }
  let streakDays = 0;
  while (days.has(cursor.toISOString().slice(0, 10))) {
    streakDays++;
    cursor.setDate(cursor.getDate() - 1);
  }

  let level = 1;
  for (let i = 1; i < LEVEL_THRESHOLDS.length; i++) {
    if (xp >= LEVEL_THRESHOLDS[i]) level = i + 1;
  }
  const base = LEVEL_THRESHOLDS[level - 1];
  const next = LEVEL_THRESHOLDS[level] ?? base + 1000;
  return { xp, streakDays, level, levelXp: xp - base, levelTarget: next - base };
}

/**
 * Mount sonrası gerçek değerleri döndüren hook.
 * İlk render (sunucu dahil) null döner → hydration uyumsuzluğu olmaz;
 * çağıran taraf `?? learner.*` ile eski statik değeri fallback gösterir.
 */
export function useLearnerStats(): LearnerStats | null {
  const [stats, setStats] = useState<LearnerStats | null>(null);
  useEffect(() => {
    setStats(computeLearnerStats());
  }, []);
  return stats;
}