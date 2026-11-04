"use client";

import { useEffect, useState } from "react";
import { loadAnswerRecords } from "./error-reason";
import { computeErrorBreakdown } from "./results-analytics";

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
  /** Bu hafta çözülen soru sayısı (son 7 gün). */
  solvedThisWeek: number;
  /** Toplam çözülen soru. */
  totalSolved: number;
  /** Kazanılan rozet sayısı. */
  badgeCount: number;
  /** H-türü dağılımı (gerçek). */
  errorBreakdown: Array<{ code: string; count: number; share: number }>;
  /** Son 5 hafta doğruluk yüzdesi (gerçek). */
  weeklyProgress: Array<{ label: string; value: number }>;
}

/** Seviye eşikleri — kümülatif XP (plan §18: sabit ve denetlenebilir). */
const LEVEL_THRESHOLDS = [0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200];

function countEarnedBadges(): number {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem("lgs_badge_progress") || "[]");
    const values = Array.isArray(stored)
      ? stored
      : stored && typeof stored === "object"
        ? Object.values(stored)
        : [];
    return values.filter(
      (badge) => badge && typeof badge === "object" && "earned" in badge && badge.earned === true
    ).length;
  } catch {
    return 0;
  }
}

/** Cevap kayıtlarından gerçek öğrenci istatistikleri. */
export function computeLearnerStats(): LearnerStats {
  const records = loadAnswerRecords();
  const correctRecords = records.filter((r) => r.correct);
  const xp = correctRecords.length * 2;

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

  // Bu hafta çözülenler (son 7 gün)
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const solvedThisWeek = records.filter((r) => new Date(r.createdAt).getTime() >= weekAgo).length;
  const totalSolved = records.length;

  const badgeCount = countEarnedBadges();

  // Gerçek H-türü dağılımı
  const errorBreakdown = computeErrorBreakdown(
    records.map((r) => ({ ...r, correct: r.correct, errorReasonCode: r.errorReasonCode }))
  );

  // Son 5 hafta doğruluk (haftalık ilerleme)
  const weeklyProgress: Array<{ label: string; value: number }> = [];
  for (let w = 4; w >= 0; w--) {
    const start = Date.now() - (w + 1) * 7 * 24 * 60 * 60 * 1000;
    const end = Date.now() - w * 7 * 24 * 60 * 60 * 1000;
    const weekRecords = records.filter((r) => {
      const t = new Date(r.createdAt).getTime();
      return t >= start && t < end;
    });
    const correct = weekRecords.filter((r) => r.correct).length;
    const total = weekRecords.length;
    weeklyProgress.push({
      label: `${5 - w}. Hafta`,
      value: total > 0 ? Math.round((weekRecords.filter((r) => r.correct).length / total) * 100) : 0,
    });
  }

  return {
    xp,
    streakDays,
    level,
    levelXp: xp - base,
    levelTarget: next - base,
    solvedThisWeek,
    totalSolved,
    badgeCount,
    errorBreakdown,
    weeklyProgress,
  };
}

/**
 * Mount sonrası gerçek değerleri döndüren hook.
 * İlk render (sunucu dahil) null döner → hydration uyumsuzluğu olmaz;
 * çağıran taraf `?? learner.*` ile eski statik değeri fallback gösterir.
 */
export function useLearnerStats(): LearnerStats | null {
  const [stats, setStats] = useState<LearnerStats | null>(null);
  useEffect(() => {
    const update = () => setStats(computeLearnerStats());
    update();
    window.addEventListener("lgs-answer-records-changed", update);
    window.addEventListener("lgs-badge-progress-changed", update);
    return () => {
      window.removeEventListener("lgs-answer-records-changed", update);
      window.removeEventListener("lgs-badge-progress-changed", update);
    };
  }, []);
  return stats;
}