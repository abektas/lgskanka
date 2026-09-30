"use client";

import { useGameRights } from "./use-game-rights";
import { learner } from "../data/nav";

/**
 * Ana sayfadaki "oyun hakkı" kartı — gerçek XP→süre ekonomisini kullanır.
 *
 * Önceden `data/nav.ts` içindeki demo `learner.gameRights` değerini gösteriyordu;
 * artık `useGameRights` ile bugünün gerçek durumunu okur.
 */
export function GameRightsCard() {
  const { ready, rights, minutesAllowance, blockedReason } = useGameRights(
    learner.xp,
    learner.gameRights,
  );

  const label = !ready
    ? "Oyun hakkı yükleniyor…"
    : blockedReason === "xp"
      ? "XP eşiği bekleniyor"
      : blockedReason
        ? "Bugün oyun hakkın doldu"
        : `${rights} oyun hakkı · ${minutesAllowance} dk`;

  const detail =
    blockedReason === "xp"
      ? "İlk soruyu çöz, oyun süresi açılsın"
      : blockedReason
        ? "Yarın sıfırlanır"
        : "Ödüller sayfasında oyna";

  return (
    <div className="mini-card">
      <span className="mini-emoji" aria-hidden="true">
        🎮
      </span>
      <span>
        {label}
        <small>{detail}</small>
      </span>
    </div>
  );
}
