"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "./icons";
import { MemoryGame } from "./memory-game";
import { Mini2048 } from "./mini-2048";
import { useGameRights } from "./use-game-rights";
import { games, memoryPairs } from "../data/content";
import { learner } from "../data/nav";

/** Plan §38: her oyun için kısa açıklama. */
const rules: Record<string, string> = {
  "Hafıza Kartları": "Terimler ile anlamlarını eşleştir. Yanlış eşleşmede kart geri kapanır, süre işler.",
  "Matematik 2048": "Düşen taşları sağa-sola kaydır; ↓ bir kare indirir, boşluk hızlı bırakır, C tutar. Eşit gruplar ×2/×4/×8 birleşip zincir oluşturur.",
  "LGS Runner": "Doğru cevabı seçtikçe karakter zıplar; yanlışta bir kalp gider. 3 kalp, 90 saniye.",
  "Hız Oyunu": "30 saniyede mümkün olduğunca çok doğru cevap ver. Hız kadar doğruluk da puanlanır.",
};

/** Henüz yazılmamış oyunlar. */
const plannedGames = new Set(["LGS Runner", "Hız Oyunu"]);

/** Sağlayıcı bilgisi: XP → oyun süresi. */
const lockedCopy: Record<string, string> = {
  xp: "XP eşiğinin altındasın. Soru çözerek XP kazandıkça oyun süresi açılır.",
  rights: "Bugünkü oyun hakkın doldu. Yarın tekrar oynayabilirsin.",
  time: "Bugünkü oyun süren doldu. Yarın tekrar oynayabilirsin.",
};

/**
 * Oyun merkezi — plan §38.
 *
 * Hafıza Kartları (§38.1) ve Mini 2048 (§38.2) gerçek oyunlardır; ikisi de aynı
 * hak/süre ekonomisini kullanır (`useGameRights`) ve XP kazandırmaz.
 * Diğer iki oyun henüz plan aşamasındadır ve dürüstçe kilitli gösterilir.
 */
export function GameCenter() {
  const [openGame, setOpenGame] = useState<string | null>(null);
  const [roundKey, setRoundKey] = useState(0);

  const { ready, rights, minutesAllowance, remainingSeconds, blockedReason, startRound, recordRound } =
    useGameRights(learner.xp, learner.gameRights);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpenGame(null);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  // Oyun açıldığında sıfırdan başlatma desteği (yeniden başlat da yeniden mount eder).
  function reopen(name: string) {
    setRoundKey((value) => value + 1);
    setOpenGame(name);
  }

  const activeGame = games.find((game) => game.name === openGame);

  return (
    <>
      <div className="game-grid">
        {games.map((game) => {
          const isPlanned = plannedGames.has(game.name);
          return (
            <button
              type="button"
              className="game-card"
              key={game.name}
              onClick={() => (isPlanned ? null : reopen(game.name))}
              disabled={isPlanned}
              style={isPlanned ? { opacity: 0.6, cursor: "default" } : undefined}
            >
              <span className="game-emoji" aria-hidden="true">
                {game.icon}
              </span>
              <span>
                <b>{game.name}</b>
                <small>
                  {isPlanned ? "Yakında · plan aşamasında" : `${game.detail} · ${game.minutes} dk`}
                </small>
              </span>
              {isPlanned ? (
                <span className="tag" aria-hidden="true">
                  Yakında
                </span>
              ) : (
                <Icon name="play" size={18} />
              )}
            </button>
          );
        })}
      </div>

      {!ready ? (
        <p className="muted-text" style={{ marginTop: 14, fontSize: 12.5 }}>
          Oyun hakkın yükleniyor…
        </p>
      ) : blockedReason ? (
        <div className="game-lock" style={{ marginTop: 14 }}>
          <span aria-hidden="true">🔒</span>
          <span>
            {lockedCopy[blockedReason]} Bugün {rights} hakkın, {minutesAllowance} dakikalık oyun
            süren var.
          </span>
        </div>
      ) : (
        <p className="muted-text" style={{ marginTop: 14, fontSize: 12.5 }}>
          Oyunlar günlük çalışma hedefini tamamladıktan sonra açılır. Bugün {rights} oyun hakkın var,
          {minutesAllowance > 0 ? ` ${minutesAllowance} dakika oynayabilirsin` : ""}.
        </p>
      )}

      {openGame && activeGame && (
        <div className="sheet" role="presentation" onClick={() => setOpenGame(null)}>
          <div
            className="sheet-card is-game"
            role="dialog"
            aria-modal="true"
            aria-labelledby="oyun-basligi"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              className="sheet-close"
              onClick={() => setOpenGame(null)}
              aria-label="Kapat"
            >
              ×
            </button>
            <div className="game-sheet-title">
              <span className="badge-emoji" aria-hidden="true">
                {activeGame.icon}
              </span>
              <h3 id="oyun-basligi">{openGame}</h3>
            </div>
            <p className="muted-text" style={{ fontSize: 13 }}>
              {rules[openGame] ?? ""}
            </p>

            {plannedGames.has(openGame) ? (
              <>
                <div className="game-lock">
                  <span aria-hidden="true">🚧</span>
                  <span>Bu oyun plan §38’de tanımlı ama henüz uygulanmadı.</span>
                </div>
                <div className="sheet-actions">
                  <Link className="btn btn-primary btn-block" href="/calis">
                    3 soruyla ısın
                  </Link>
                  <button
                    type="button"
                    className="btn btn-ghost btn-block"
                    onClick={() => setOpenGame(null)}
                  >
                    Tamam
                  </button>
                </div>
              </>
            ) : blockedReason ? (
              <>
                <div className="game-lock">
                  <span aria-hidden="true">🔒</span>
                  <span>{lockedCopy[blockedReason]}</span>
                </div>
                <div className="sheet-actions">
                  <Link className="btn btn-primary btn-block" href="/calis">
                    Soru çöz, XP kazan
                  </Link>
                  <button
                    type="button"
                    className="btn btn-ghost btn-block"
                    onClick={() => setOpenGame(null)}
                  >
                    Tamam
                  </button>
                </div>
              </>
            ) : openGame === "Hafıza Kartları" ? (
              <MemoryGame
                key={roundKey}
                pairs={memoryPairs}
                rightsLeft={rights}
                remainingSeconds={remainingSeconds}
                onRoundStart={startRound}
                onRoundEnd={recordRound}
                onExit={() => setOpenGame(null)}
              />
            ) : (
              <Mini2048
                key={roundKey}
                rightsLeft={rights}
                remainingSeconds={remainingSeconds}
                onRoundStart={startRound}
                onRoundEnd={recordRound}
                onExit={() => setOpenGame(null)}
              />
            )}
          </div>
        </div>
      )}
    </>
  );
}
