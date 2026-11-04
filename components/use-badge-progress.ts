"use client";

import { useEffect, useState } from "react";
import { badges, type Badge } from "../data/content";
import { loadAnswerRecords } from "../lib/error-reason";
import { computeLearnerStats } from "../lib/learner-stats";
import { pushBadgeProgress } from "../lib/sync";

const BADGE_STORAGE_KEY = "lgs_badge_progress";

function readStoredBadges(): Badge[] {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(BADGE_STORAGE_KEY) || "[]");
    const values = Array.isArray(stored)
      ? stored
      : stored && typeof stored === "object"
        ? Object.entries(stored).map(([name, value]) => ({ name, ...(value as object) }))
        : [];
    return badges.map((base) => {
      const saved = values.find((value) => value && typeof value === "object" && value.name === base.name);
      return saved ? { ...base, ...saved } as Badge : { ...base, earned: false };
    });
  } catch {
    return badges.map((badge) => ({ ...badge, earned: false }));
  }
}

/** Rozet açma kriterlerini kontrol eder ve earned durumunu günceller. */
export function useBadgeProgress() {
  const [badgeList, setBadgeList] = useState<Badge[]>(readStoredBadges);

  useEffect(() => {
    const update = () => {
    const records = loadAnswerRecords();
    const totalSolved = records.length;

    // H4 oranı
    const h4Count = records.filter((r) => !r.correct && r.errorReasonCode === "H4").length;
    const totalWrong = records.filter((r) => !r.correct).length;
    const h4Rate = totalWrong > 0 ? h4Count / totalWrong : 0;

    // Toplam çözülen soru
    const correctCount = records.filter((r) => r.correct).length;

    // Günlük seri: computeLearnerStats() ile aynı kural (sunucu kayıtlarından)
    const currentStreak = computeLearnerStats().streakDays;

    // Sunucudan zaten kazanılmış rozetler + yeni kazanım
    const serverEarned = new Set(
      readStoredBadges().filter((badge) => badge.earned).map((badge) => badge.name)
    );

    // Use imported badges as base, not state (avoids infinite loop)
    const updated = badges.map((badge) => {
      if (serverEarned.has(badge.name)) return { ...badge, earned: true };

      let shouldEarn = false;
      switch (badge.name) {
        case "İlk Adım":
          shouldEarn = totalSolved >= 1;
          break;
        case "4 Gün Seri":
          shouldEarn = currentStreak >= 4;
          break;
        case "İlk Hata Analizi":
          shouldEarn = records.some((r) => !r.correct && r.errorReasonCode);
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
      const earned = shouldEarn || serverEarned.has(badge.name);
      return { ...badge, earned };
    });

    setBadgeList(updated);
    localStorage.setItem(BADGE_STORAGE_KEY, JSON.stringify(updated));
    window.dispatchEvent(new Event("lgs-badge-progress-changed"));

    // Kazanılmış rozetleri sunucuya yaz (fire-and-forget)
    const toPush: Record<string, { earned: boolean; earned_at: string | null; progress: number }> = {};
    for (const b of updated) {
      if (b.earned) toPush[b.name] = { earned: true, earned_at: new Date().toISOString(), progress: 100 };
    }
    if (Object.keys(toPush).length > 0) pushBadgeProgress(toPush);
    };
    update();
    window.addEventListener("lgs-answer-records-changed", update);
    return () => window.removeEventListener("lgs-answer-records-changed", update);
  }, []);

  return badgeList;
}

/** Manuel rozet vermek için (test/debug). */
export function unlockBadge(badgeName: string) {
  const updated = readStoredBadges().map((badge) =>
    badge.name === badgeName ? { ...badge, earned: true } : badge
  );
  try {
    localStorage.setItem(BADGE_STORAGE_KEY, JSON.stringify(updated));
    window.dispatchEvent(new Event("lgs-badge-progress-changed"));
  } catch {}
}