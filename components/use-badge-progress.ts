"use client";

import { useEffect, useMemo, useState } from "react";
import { badges, type Badge } from "../data/content";
import { loadAnswerRecords } from "../lib/error-reason";
import { computeUnitMasteries } from "../lib/mastery";

const BADGE_STORAGE_KEY = "lgs_badge_progress";

/** Rozet açma kriterlerini kontrol eder ve earned durumunu günceller. */
export function useBadgeProgress() {
  const [badgeList, setBadgeList] = useState<Badge[]>(() => {
    // Initialize from localStorage if available
    try {
      const stored = JSON.parse(localStorage.getItem(BADGE_STORAGE_KEY) || "[]");
      if (stored.length === badges.length) return stored as Badge[];
    } catch {}
    return badges;
  });

  useEffect(() => {
    const records = loadAnswerRecords();
    const masteries = computeUnitMasteries(records);
    const totalSolved = records.length;

    // H4 oranı
    const h4Count = records.filter(r => !r.correct && r.errorReasonCode === "H4").length;
    const totalWrong = records.filter(r => !r.correct).length;
    const h4Rate = totalWrong > 0 ? h4Count / totalWrong : 0;

    // Toplam çözülen soru
    const correctCount = records.filter(r => r.correct).length;

    // Günlük seri (localStorage'dan)
    let currentStreak = 0;
    try {
      const streakData = JSON.parse(localStorage.getItem("lgs_streak") || "{}");
      currentStreak = streakData.currentStreak || 0;
    } catch {}

    // Use imported badges as base, not state (avoids infinite loop)
    const updated = badges.map((badge) => {
      if (badge.earned) return badge;

      let shouldEarn = false;
      switch (badge.name) {
        case "İlk Adım":
          shouldEarn = totalSolved >= 1;
          break;
        case "4 Gün Seri":
          shouldEarn = currentStreak >= 4;
          break;
        case "İlk Hata Analizi":
          shouldEarn = records.some(r => !r.correct && r.errorReasonCode);
          break;
        case "İşlem Ustası":
          shouldEarn = h4Rate < 0.1 && totalWrong >= 10;
          break;
        case "Hedefe Sadık":
          shouldEarn = currentStreak >= 7;
          break;
        case "Kitap Kurdu":
          shouldEarn = totalSolved >= 50;
          break;
        case "Hızlı Düşünen":
          // testte ilk 10'a girme - şimdilik demo false
          shouldEarn = false;
          break;
        case "7 Gün Seri":
          shouldEarn = currentStreak >= 7;
          break;
      }
      return shouldEarn ? { ...badge, earned: true } : badge;
    });

    setBadgeList(updated);
    localStorage.setItem(BADGE_STORAGE_KEY, JSON.stringify(updated));
  }, []); // Run once on mount

  return badgeList;
}

/** Manuel rozet vermek için (test/debug). */
export function unlockBadge(badgeName: string) {
  try {
    const stored = JSON.parse(localStorage.getItem(BADGE_STORAGE_KEY) || "[]");
    const updated = stored.map((b: Badge) => b.name === badgeName ? { ...b, earned: true } : b);
    localStorage.setItem(BADGE_STORAGE_KEY, JSON.stringify(updated));
  } catch {}
}