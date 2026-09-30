"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { MemoryPair } from "../data/content";

/**
 * Hafıza Kartları — plan §38.1.
 *
 * 12 kart / 6 çift · kart çevirme · eşleşme · yanlış eşleşmede kapanma · hamle sayısı · süre ·
 * tamamlanma mesajı · yeniden başlat · geri dön.
 *
 * Oyun XP kazandırmaz; ilk kart çevrildiğinde 1 oyun hakkı harcar ve geçen süre günlük
 * oyun süresinden düşülür. Hak/süre sahibi üst bileşendir (`useGameRights`).
 */

type Card = {
  key: string;
  pairId: string;
  kind: "term" | "definition";
  label: string;
  subject: string;
};

type Status = "idle" | "playing" | "done" | "timeup";

/** Yanlış eşleşmede kartların açık kalma süresi (ms). */
const MISMATCH_DELAY_MS = 900;

/** Fisher–Yates ile karıştırılmış 12 kartlık deste üretir. */
function buildDeck(pairs: MemoryPair[]): Card[] {
  const deck: Card[] = pairs.flatMap((pair) => [
    {
      key: `${pair.id}-term`,
      pairId: pair.id,
      kind: "term" as const,
      label: pair.term,
      subject: pair.subject,
    },
    {
      key: `${pair.id}-definition`,
      pairId: pair.id,
      kind: "definition" as const,
      label: pair.definition,
      subject: pair.subject,
    },
  ]);

  for (let i = deck.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [deck[i], deck[j]] = [deck[j], deck[i]];
  }
  return deck;
}

/** 95 → "01:35" */
export function formatClock(totalSeconds: number): string {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const minutes = String(Math.floor(safe / 60)).padStart(2, "0");
  const seconds = String(safe % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

export function MemoryGame({
  pairs,
  rightsLeft,
  remainingSeconds,
  onRoundStart,
  onRoundEnd,
  onExit,
}: {
  pairs: MemoryPair[];
  /** Bugün kalan tur hakkı (yeni tur için 1 hak gerekir). */
  rightsLeft: number;
  /** Bugün kalan oyun süresi (saniye). */
  remainingSeconds: number;
  onRoundStart: () => void;
  onRoundEnd: (seconds: number) => void;
  onExit: () => void;
}) {
  const [deck, setDeck] = useState<Card[]>([]);
  const [flipped, setFlipped] = useState<string[]>([]);
  const [matched, setMatched] = useState<string[]>([]);
  const [moves, setMoves] = useState(0);
  const [seconds, setSeconds] = useState(0);
  const [timeLeft, setTimeLeft] = useState(Math.max(0, remainingSeconds));
  const [status, setStatus] = useState<Status>("idle");
  const [locked, setLocked] = useState(false);

  /** Bu turda geçen süre (kayıt ve raporlama için). */
  const elapsedRef = useRef(0);
  /** Bu turun süresi bir kez kaydedilsin. */
  const endedRef = useRef(false);
  const mismatchTimer = useRef<number | null>(null);

  const endRoundRef = useRef(onRoundEnd);
  useEffect(() => {
    endRoundRef.current = onRoundEnd;
  }, [onRoundEnd]);

  /** Turluk süreyi tek seferlik kaydeder (tamamlanma, süre bitimi, yeniden başlatma, çıkış). */
  const endRound = useCallback(() => {
    if (endedRef.current) return;
    endedRef.current = true;
    endRoundRef.current(elapsedRef.current);
  }, []);

  // Deste yalnızca istemcide kurulur (sunucu/istemci karışıklığı olmasın).
  useEffect(() => {
    setDeck(buildDeck(pairs));
    setTimeLeft(Math.max(0, remainingSeconds));
  }, [pairs, remainingSeconds]);

  // Bileşen kalkarken açık kalan turu kapat: geçen süre boşa gitmesin.
  useEffect(() => {
    return () => {
      endRound();
      if (mismatchTimer.current !== null) window.clearTimeout(mismatchTimer.current);
    };
  }, [endRound]);

  // Süre sayacı: hem tur süresi hem günlük kalan süre işler.
  useEffect(() => {
    if (status !== "playing") return;
    const id = window.setInterval(() => {
      elapsedRef.current += 1;
      setSeconds((value) => value + 1);
      setTimeLeft((value) => Math.max(0, value - 1));
    }, 1000);
    return () => window.clearInterval(id);
  }, [status]);

  // Günlük süre biterse tur biter (plan §18: günlük 10 dakika sınırı).
  useEffect(() => {
    if (status === "playing" && timeLeft <= 0) setStatus("timeup");
  }, [status, timeLeft]);

  // Tur bittiğinde süreyi kaydet.
  useEffect(() => {
    if (status === "done" || status === "timeup") endRound();
  }, [status, endRound]);

  const matchedPairs = matched.length / 2;

  function flip(key: string) {
    if (locked || status === "done" || status === "timeup") return;
    if (flipped.includes(key) || matched.includes(key)) return;

    if (status === "idle") {
      setStatus("playing");
      onRoundStart();
    }

    const next = [...flipped, key];
    setFlipped(next);
    if (next.length < 2) return;

    const [first, second] = next
      .map((cardKey) => deck.find((card) => card.key === cardKey))
      .filter((card): card is Card => Boolean(card));
    if (!first || !second) return;

    setMoves((value) => value + 1);

    if (first.pairId === second.pairId) {
      const nextMatched = [...matched, first.key, second.key];
      setMatched(nextMatched);
      setFlipped([]);
      if (nextMatched.length === deck.length) setStatus("done");
      return;
    }

    setLocked(true);
    mismatchTimer.current = window.setTimeout(() => {
      setFlipped([]);
      setLocked(false);
      mismatchTimer.current = null;
    }, MISMATCH_DELAY_MS);
  }

  function restart() {
    endRound();
    endedRef.current = false;
    elapsedRef.current = 0;
    if (mismatchTimer.current !== null) {
      window.clearTimeout(mismatchTimer.current);
      mismatchTimer.current = null;
    }
    setDeck(buildDeck(pairs));
    setFlipped([]);
    setMatched([]);
    setMoves(0);
    setSeconds(0);
    setLocked(false);
    setStatus("idle");
  }

  function exit() {
    endRound();
    onExit();
  }

  const finished = status === "done" || status === "timeup";
  const canRestart = rightsLeft > 0 && timeLeft > 0;

  return (
    <div className="memory-wrap">
      <div className="game-hud">
        <div>
          <small>Hamle</small>
          <b>{moves}</b>
        </div>
        <div>
          <small>Tur süresi</small>
          <b>{formatClock(seconds)}</b>
        </div>
        <div>
          <small>Eşleşen</small>
          <b>
            {matchedPairs} / {pairs.length}
          </b>
        </div>
        <div>
          <small>Bugün kalan süre</small>
          <b>{formatClock(timeLeft)}</b>
        </div>
      </div>

      <div className="memory-board" role="group" aria-label="Hafıza kartları (6 çift)">
        {deck.map((card) => {
          const isMatched = matched.includes(card.key);
          const isUp = isMatched || flipped.includes(card.key);
          return (
            <button
              type="button"
              key={card.key}
              className={`memory-card${isUp ? " is-up" : ""}${isMatched ? " is-matched" : ""}`}
              onClick={() => flip(card.key)}
              disabled={isMatched || finished}
              aria-pressed={isUp}
              aria-label={isUp ? `${card.subject} · ${card.label}` : "Kapalı kart — çevirmek için tıkla"}
            >
              {isUp ? (
                <>
                  <span className="memory-kind">
                    {card.kind === "term" ? "Kavram" : "Karşılık"}
                    <span className="sr-only"> — {card.subject}</span>
                  </span>
                  <span>{card.label}</span>
                </>
              ) : (
                <span className="memory-mark" aria-hidden="true">
                  ?
                </span>
              )}
            </button>
          );
        })}
      </div>

      {status === "idle" && (
        <p className="memory-note">
          Kart çevirip kavramı karşılığıyla eşleştir. Yanlış eşleşmede kartlar geri kapanır.{" "}
          <strong>İlk kartı çevirdiğinde 1 oyun hakkı harcanır.</strong> Bugün {rightsLeft} tur hakkın
          kaldı.
        </p>
      )}

      {status === "playing" && (
        <p className="memory-note" aria-live="polite">
          {rightsLeft > 0
            ? `Tur devam ediyor · ${formatClock(timeLeft)} süre kaldı.`
            : "Bu turdan sonra bugünkü oyun hakkın doluyor."}
        </p>
      )}

      {status === "done" && (
        <div className="result is-ok">
          <b>🎉 Tebrikler! {pairs.length} çiftin tamamını eşleştirdin.</b>
          <p>
            {moves} hamlede ve {formatClock(seconds)} sürede bitirdin. Bu tur 1 oyun hakkı harcadı;
            oyun XP kazandırmaz. Şimdi öğrendiğini soruyla doğrulayalım.
          </p>
        </div>
      )}

      {status === "timeup" && (
        <div className="result is-bad">
          <b>⏱️ Bugünkü oyun süren doldu.</b>
          <p>
            Günlük oyun sınırı 10 dakika. Kalan kartlar yarına kalıyor; bugünkü ilerlemen kaydedildi.
          </p>
        </div>
      )}

      {finished && (
        <div className="memory-review-wrap">
          <p className="memory-note">Bu turda tekrar ettiğin kavramlar:</p>
          <ul className="memory-review">
            {pairs.map((pair) => (
              <li key={pair.id}>
                <strong>{pair.subject}</strong> · {pair.term} = {pair.definition}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="sheet-actions">
        <button
          type="button"
          className="btn btn-primary btn-block"
          onClick={restart}
          disabled={!canRestart}
        >
          {canRestart ? "Yeniden başla (yeni deste, 1 hak)" : "Yeniden başlatılamaz — hak/süre yok"}
        </button>
        <button type="button" className="btn btn-ghost btn-block" onClick={exit}>
          Geri dön
        </button>
      </div>

      <p className="privacy-notice" role="note">
        Oyun turları öğrenmenin yerine geçmez: XP kazandırmaz, yalnızca çalışma hedefini
        tamamladıktan sonra kazandığın hakkı ve süreyi kullanır.
      </p>
    </div>
  );
}
