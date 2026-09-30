"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Matematik 2048 — plan §38.2.
 *
 * 4×4 taşa · yukarı/aşağı/sağ/sol · birleşme · skor · reset · game over · kazanma durumu.
 *
 * Varyant: klasik 2048'den farklı olarak 1024 taşında biter (LGS hazırlığı için anlamlı
 * eşik). Sayılar görsel olarak aynı kalır, mantık yine gerçek birleşme oyunudur.
 *
 * Oyun XP kazandırmaz; ilk hamlede 1 oyun hakkı harcanır ve geçen süre günlük
 * oyun süresinden düşülür. Hak/süre sahibi üst bileşendir (`useGameRights`).
 */

type Grid = number[][];
type Status = "idle" | "playing" | "won" | "over" | "timeup";
type Direction = "left" | "right" | "up" | "down";

/** Plan §38.2: 4×4 taşa. */
const SIZE = 4;
/** Klasik 2048 iki taş ile başlar. */
const SPAWN_TILES = 2;
/** LGS hazırlığı için anlamlı eşik. */
const WIN_TILE = 1024;

/** 95 → "01:35" */
export function formatClock(totalSeconds: number): string {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const minutes = String(Math.floor(safe / 60)).padStart(2, "0");
  const seconds = String(safe % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function createGrid(): Grid {
  return Array.from({ length: SIZE }, () => Array<number>(SIZE).fill(0));
}

function emptyCells(grid: Grid): Array<[number, number]> {
  const cells: Array<[number, number]> = [];
  for (let r = 0; r < SIZE; r += 1) {
    for (let c = 0; c < SIZE; c += 1) {
      if (grid[r][c] === 0) cells.push([r, c]);
    }
  }
  return cells;
}

/** Boş hücreye rastgele 2 veya 4 koyar. */
function spawn(grid: Grid): Grid {
  const cells = emptyCells(grid);
  if (cells.length === 0) return grid;
  const [r, c] = cells[Math.floor(Math.random() * cells.length)];
  const next = grid.map((row) => [...row]);
  next[r][c] = Math.random() < 0.9 ? 2 : 4;
  return next;
}

function addRandomTiles(grid: Grid): Grid {
  let next = grid;
  for (let i = 0; i < SPAWN_TILES; i += 1) next = spawn(next);
  return next;
}

/** Bir satırı sola kaydırıp aynıları birleştirir. */
function mergeRow(row: number[]): { tiles: number[]; score: number } {
  const tiles = row.filter((value) => value !== 0);
  const out: number[] = [];
  let score = 0;
  for (let i = 0; i < tiles.length; i += 1) {
    if (i + 1 < tiles.length && tiles[i] === tiles[i + 1]) {
      const merged = tiles[i] * 2;
      out.push(merged);
      score += merged;
      i += 1;
    } else {
      out.push(tiles[i]);
    }
  }
  while (out.length < SIZE) out.push(0);
  return { tiles: out, score };
}

/** Yönü uygular; tahta değiştiyse `moved` true döner. */
function move(grid: Grid, direction: Direction): { grid: Grid; score: number; moved: boolean } {
  let gained = 0;
  const next = createGrid();

  for (let i = 0; i < SIZE; i += 1) {
    let line: number[];
    if (direction === "left") line = [...grid[i]];
    else if (direction === "right") line = [...grid[i]].reverse();
    else if (direction === "up") line = grid.map((row) => row[i]);
    else line = grid.map((row) => row[i]).reverse();

    const { tiles, score } = mergeRow(line);
    gained += score;

    if (direction === "left") next[i] = tiles;
    else if (direction === "right") next[i] = [...tiles].reverse();
    else if (direction === "up") next[i] = tiles;
    else next[i] = [...tiles].reverse();
  }

  let moved = false;
  outer: for (let r = 0; r < SIZE; r += 1) {
    for (let c = 0; c < SIZE; c += 1) {
      if (grid[r][c] !== next[r][c]) {
        moved = true;
        break outer;
      }
    }
  }

  return { grid: next, score: gained, moved };
}

function canMove(grid: Grid): boolean {
  for (let r = 0; r < SIZE; r += 1) {
    for (let c = 0; c < SIZE; c += 1) {
      if (grid[r][c] === 0) return true;
      const v = grid[r][c];
      if (c + 1 < SIZE && grid[r][c + 1] === v) return true;
      if (r + 1 < SIZE && grid[r + 1][c] === v) return true;
    }
  }
  return false;
}

function highestTile(grid: Grid): number {
  return grid.reduce((max, row) => Math.max(max, ...row), 0);
}

function tileLabel(value: number): string {
  return String(value);
}

export function Mini2048({
  rightsLeft,
  remainingSeconds,
  onRoundStart,
  onRoundEnd,
  onExit,
}: {
  rightsLeft: number;
  remainingSeconds: number;
  onRoundStart: () => void;
  onRoundEnd: (seconds: number) => void;
  onExit: () => void;
}) {
  const [grid, setGrid] = useState<Grid>(() => addRandomTiles(createGrid()));
  const [score, setScore] = useState(0);
  const [best, setBest] = useState(0);
  const [moves, setMoves] = useState(0);
  const [status, setStatus] = useState<Status>("idle");
  const [timeLeft, setTimeLeft] = useState(Math.max(0, remainingSeconds));

  const elapsedRef = useRef(0);
  const endedRef = useRef(false);
  const gridRef = useRef(grid);
  const statusRef = useRef(status);
  const endRoundRef = useRef(onRoundEnd);

  gridRef.current = grid;
  statusRef.current = status;

  useEffect(() => {
    endRoundRef.current = onRoundEnd;
  }, [onRoundEnd]);

  const endRound = useCallback(() => {
    if (endedRef.current) return;
    endedRef.current = true;
    endRoundRef.current(elapsedRef.current);
  }, []);

  useEffect(() => {
    setTimeLeft(Math.max(0, remainingSeconds));
  }, [remainingSeconds]);

  // Bileşen kalkarken açık turu kapat: geçen süre boşa gitmesin.
  useEffect(() => {
    return () => {
      endRound();
    };
  }, [endRound]);

  // Süre sayacı yalnızca oynanırken işler.
  useEffect(() => {
    if (status !== "playing") return;
    const id = window.setInterval(() => {
      elapsedRef.current += 1;
      setTimeLeft((value) => Math.max(0, value - 1));
    }, 1000);
    return () => window.clearInterval(id);
  }, [status]);

  useEffect(() => {
    if (status === "playing" && timeLeft <= 0) setStatus("timeup");
  }, [status, timeLeft]);

  useEffect(() => {
    if (status === "won" || status === "over" || status === "timeup") endRound();
  }, [status, endRound]);

  function restart() {
    endRound();
    endedRef.current = false;
    elapsedRef.current = 0;
    setGrid(addRandomTiles(createGrid()));
    setScore(0);
    setBest(0);
    setMoves(0);
    setTimeLeft(Math.max(0, remainingSeconds));
    setStatus("idle");
  }

  function exit() {
    endRound();
    onExit();
  }

  /** Tek giriş noktası: yön uygular, hak/skor/güncelleme yapar. */
  const push = useCallback((direction: Direction) => {
    const current = statusRef.current;
    if (current !== "idle" && current !== "playing" && current !== "won") return;

    if (current === "idle") {
      statusRef.current = "playing";
      setStatus("playing");
      onRoundStart();
    }

    const result = move(gridRef.current, direction);
    if (!result.moved) return;

    const withSpawn = addRandomTiles(result.grid);
    gridRef.current = withSpawn;
    setGrid(withSpawn);
    setScore((value) => {
      const next = value + result.score;
      setBest((previous) => (next > previous ? next : previous));
      return next;
    });
    setMoves((value) => value + 1);

    if (highestTile(withSpawn) >= WIN_TILE) {
      statusRef.current = "won";
      setStatus("won");
      return;
    }
    if (!canMove(withSpawn)) {
      statusRef.current = "over";
      setStatus("over");
    }
  }, [onRoundStart]);

  // Klavye: ok tuşları + WASD.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const map: Record<string, Direction> = {
        ArrowLeft: "left",
        ArrowRight: "right",
        ArrowUp: "up",
        ArrowDown: "down",
        a: "left",
        d: "right",
        w: "up",
        s: "down",
      };
      const direction = map[event.key];
      if (!direction) return;
      // Sayfa kaymasini engelle (oyun alanindayken).
      event.preventDefault();
      push(direction);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [push]);

  const finished = status === "won" || status === "over" || status === "timeup";
  const canRestart = rightsLeft > 0 && timeLeft > 0;
  const tile = highestTile(grid);

  return (
    <div className="g2048">
      <div className="game-hud">
        <div>
          <small>Skor</small>
          <b>{score}</b>
        </div>
        <div>
          <small>En iyi</small>
          <b>{best}</b>
        </div>
        <div>
          <small>Hamle</small>
          <b>{moves}</b>
        </div>
        <div>
          <small>Bugün kalan süre</small>
          <b>{formatClock(timeLeft)}</b>
        </div>
      </div>

      <div className="g2048-board" role="group" aria-label="2048 taşası, 4 çarpı 4">
        {grid.map((row, r) =>
          row.map((value, c) => (
            <div
              className={`g2048-tile${value === 0 ? " is-empty" : ""}${value >= 512 ? " is-big" : ""}`}
              key={`${r}-${c}`}
            >
              {value > 0 ? <span>{tileLabel(value)}</span> : null}
            </div>
          )),
        )}
      </div>

      <div className="g2048-pad" role="group" aria-label="Yön tuşları">
        <button type="button" className="g2048-key is-up" onClick={() => push("up")} aria-label="Yukarı">
          ↑
        </button>
        <button type="button" className="g2048-key is-left" onClick={() => push("left")} aria-label="Sol">
          ←
        </button>
        <button
          type="button"
          className="g2048-key is-right"
          onClick={() => push("right")}
          aria-label="Sağ"
        >
          →
        </button>
        <button
          type="button"
          className="g2048-key is-down"
          onClick={() => push("down")}
          aria-label="Aşağı"
        >
          ↓
        </button>
      </div>

      {status === "idle" && (
        <p className="memory-note">
          Aynı sayıları birleştirerek <strong>{WIN_TILE}</strong> değerine ulaş. Ok tuşları veya
          ekrandaki yön tuşları.
          <strong> İlk hamlede 1 oyun hakkı harcanır.</strong> Bugün {rightsLeft} tur hakkın kaldı.
        </p>
      )}

      {status === "playing" && (
        <p className="memory-note" aria-live="polite">
          En yüksek taş: <b>{tileLabel(tile)}</b> ·{" "}
          {rightsLeft > 0
            ? `${formatClock(timeLeft)} süre kaldı.`
            : "Bu turdan sonra bugünkü oyun hakkın doluyor."}
        </p>
      )}

      {status === "won" && (
        <div className="result is-ok">
          <b>Tebrikler! {WIN_TILE} taşına ulaştın.</b>
          <p>
            {moves} hamlede ve {formatClock(elapsedRef.current)} sürede bitirdin. Bu tur 1 oyun hakkı
            harcadı; oyun XP kazandırmaz. En yüksek taş: {tileLabel(tile)}.
          </p>
        </div>
      )}

      {status === "over" && (
        <div className="result is-bad">
          <b>Taşa hareket edemiyor.</b>
          <p>
            En yüksek taş: <b>{tileLabel(tile)}</b> · Skor: <b>{score}</b>. Boş kare yok ve aynı komşular
            yan yana değil. Yeni bir taşta ile tekrar dene.
          </p>
        </div>
      )}

      {status === "timeup" && (
        <div className="result is-bad">
          <b>Bugünkü oyun süren doldu.</b>
          <p>
            Günlük oyun sınırı 10 dakika. Bugünkü ilerlemen kaydedildi; kalan hamle hakkın yarına
            kalıyor.
          </p>
        </div>
      )}

      <div className="sheet-actions">
        <button type="button" className="btn btn-primary btn-block" onClick={restart} disabled={!canRestart}>
          {canRestart ? "Yeniden başlat (yeni taşta, 1 hak)" : "Yeniden başlatılamaz — hak/süre yok"}
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
