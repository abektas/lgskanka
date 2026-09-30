"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Grid = number[][];
type Status = "idle" | "playing" | "won" | "over" | "timeup";
type ActiveTile = { row: number; col: number; value: number };
type Control = "left" | "right" | "down" | "drop";

const ROWS = 10;
const COLS = 6;
const WIN_TILE = 2048;
const GRAVITY_MS = 850;

export function formatClock(totalSeconds: number): string {
  const safe = Math.max(0, Math.floor(totalSeconds));
  return `${String(Math.floor(safe / 60)).padStart(2, "0")}:${String(safe % 60).padStart(2, "0")}`;
}

function emptyGrid(): Grid {
  return Array.from({ length: ROWS }, () => Array<number>(COLS).fill(0));
}

function randomTile(): number {
  return Math.random() < 0.9 ? 2 : 4;
}

function settle(grid: Grid): Grid {
  const next = emptyGrid();
  for (let col = 0; col < COLS; col += 1) {
    const values = grid.map((row) => row[col]).filter(Boolean);
    const offset = ROWS - values.length;
    values.forEach((value, index) => { next[offset + index][col] = value; });
  }
  return next;
}

/** Merge adjacent equal tiles, letting gravity create further combinations. */
function mergeCascade(source: Grid): { grid: Grid; score: number; highest: number } {
  let grid = settle(source);
  let score = 0;
  let highest = Math.max(...grid.flat());
  for (;;) {
    let pair: [number, number, number, number] | null = null;
    for (let row = ROWS - 1; row >= 0 && !pair; row -= 1) {
      for (let col = 0; col < COLS && !pair; col += 1) {
        const value = grid[row][col];
        if (!value) continue;
        if (col + 1 < COLS && grid[row][col + 1] === value) pair = [row, col, row, col + 1];
        else if (row + 1 < ROWS && grid[row + 1][col] === value) pair = [row, col, row + 1, col];
      }
    }
    if (!pair) break;
    const [row, col, otherRow, otherCol] = pair;
    const merged = grid[row][col] * 2;
    const next = grid.map((line) => [...line]);
    next[row][col] = merged;
    next[otherRow][otherCol] = 0;
    score += merged;
    highest = Math.max(highest, merged);
    grid = settle(next);
  }
  return { grid, score, highest };
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
  const [grid, setGrid] = useState<Grid>(emptyGrid);
  const [active, setActive] = useState<ActiveTile>({ row: 0, col: 2, value: randomTile() });
  const [nextValue, setNextValue] = useState(randomTile);
  const [score, setScore] = useState(0);
  const [best, setBest] = useState(0);
  const [moves, setMoves] = useState(0);
  const [status, setStatus] = useState<Status>("idle");
  const [timeLeft, setTimeLeft] = useState(Math.max(0, remainingSeconds));

  const elapsedRef = useRef(0);
  const endedRef = useRef(false);
  const startedRef = useRef(false);
  const gridRef = useRef(grid);
  const activeRef = useRef(active);
  const statusRef = useRef(status);
  const endRoundRef = useRef(onRoundEnd);
  gridRef.current = grid;
  activeRef.current = active;
  statusRef.current = status;

  useEffect(() => { endRoundRef.current = onRoundEnd; }, [onRoundEnd]);
  const endRound = useCallback(() => {
    if (endedRef.current) return;
    endedRef.current = true;
    endRoundRef.current(elapsedRef.current);
  }, []);
  useEffect(() => setTimeLeft(Math.max(0, remainingSeconds)), [remainingSeconds]);
  useEffect(() => () => { if (startedRef.current) endRound(); }, [endRound]);

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
    if (status === "over" || status === "timeup") endRound();
  }, [status, endRound]);

  const begin = useCallback(() => {
    if (statusRef.current === "idle") {
      startedRef.current = true;
      statusRef.current = "playing";
      setStatus("playing");
      onRoundStart();
    }
  }, [onRoundStart]);

  const lockTile = useCallback((tile: ActiveTile) => {
    const board = gridRef.current.map((row) => [...row]);
    board[tile.row][tile.col] = tile.value;
    const resolved = mergeCascade(board);
    gridRef.current = resolved.grid;
    setGrid(resolved.grid);
    setScore((current) => {
      const updated = current + resolved.score;
      setBest((previous) => Math.max(previous, updated));
      return updated;
    });
    setMoves((current) => current + 1);
    const nextActive = { row: 0, col: 2, value: nextValue };
    const newNext = randomTile();
    setNextValue(newNext);
    if (resolved.highest >= WIN_TILE) {
      setActive(nextActive);
      activeRef.current = nextActive;
      statusRef.current = "won";
      setStatus("won");
      return;
    }
    if (resolved.grid[0][nextActive.col] !== 0) {
      statusRef.current = "over";
      setStatus("over");
      return;
    }
    setActive(nextActive);
    activeRef.current = nextActive;
  }, [nextValue]);

  const control = useCallback((action: Control) => {
    const currentStatus = statusRef.current;
    if (currentStatus !== "idle" && currentStatus !== "playing") return;
    if (currentStatus === "idle") begin();
    const tile = activeRef.current;
    if (action === "left" || action === "right") {
      const col = tile.col + (action === "left" ? -1 : 1);
      if (col >= 0 && col < COLS && gridRef.current[tile.row][col] === 0) {
        const moved = { ...tile, col };
        activeRef.current = moved;
        setActive(moved);
      }
      return;
    }
    let row = tile.row;
    while (row + 1 < ROWS && gridRef.current[row + 1][tile.col] === 0) row += 1;
    if (action === "drop") {
      lockTile({ ...tile, row });
      return;
    }
    if (row > tile.row) {
      const moved = { ...tile, row };
      activeRef.current = moved;
      setActive(moved);
    } else {
      lockTile(tile);
    }
  }, [begin, lockTile]);

  useEffect(() => {
    if (status !== "playing") return;
    const id = window.setInterval(() => {
      const tile = activeRef.current;
      if (tile.row + 1 < ROWS && gridRef.current[tile.row + 1][tile.col] === 0) {
        const moved = { ...tile, row: tile.row + 1 };
        activeRef.current = moved;
        setActive(moved);
      } else {
        lockTile(tile);
      }
    }, GRAVITY_MS);
    return () => window.clearInterval(id);
  }, [status, lockTile]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target;
      if (target instanceof HTMLElement && target.closest("button, input, textarea, select")) return;
      const key = event.key.toLowerCase();
      const action: Control | undefined =
        key === "arrowleft" || key === "a" ? "left" :
        key === "arrowright" || key === "d" ? "right" :
        key === "arrowdown" || key === "s" ? "down" :
        key === " " ? "drop" : undefined;
      if (!action) return;
      event.preventDefault();
      control(action);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [control]);

  function restart() {
    endRound();
    endedRef.current = false;
    startedRef.current = false;
    elapsedRef.current = 0;
    const fresh = emptyGrid();
    gridRef.current = fresh;
    setGrid(fresh);
    const first = randomTile();
    setActive({ row: 0, col: 2, value: first });
    activeRef.current = { row: 0, col: 2, value: first };
    setNextValue(randomTile());
    setScore(0);
    setBest(0);
    setMoves(0);
    setTimeLeft(Math.max(0, remainingSeconds));
    statusRef.current = "idle";
    setStatus("idle");
  }

  function exit() {
    if (startedRef.current) endRound();
    onExit();
  }

  const canRestart = rightsLeft > 0 && timeLeft > 0;
  const highest = Math.max(...grid.flat(), active.value);

  return (
    <div className="g2048">
      <div className="game-hud">
        <div><small>Skor</small><b>{score}</b></div>
        <div><small>En iyi</small><b>{best}</b></div>
        <div><small>Birleşen</small><b>{moves}</b></div>
        <div><small>Kalan süre</small><b>{formatClock(timeLeft)}</b></div>
      </div>

      <div className="g2048-stage">
        <div className="g2048-board" role="grid" aria-label="Matematik 2048, 6 sütun ve 10 satır">
          {grid.map((row, r) => row.map((value, c) => (
            <div className={`g2048-tile${value ? "" : " is-empty"}${value >= 512 ? " is-big" : ""}`} role="gridcell" aria-label={value ? String(value) : "Boş"} key={`${r}-${c}`}>
              {value ? <span>{value}</span> : null}
            </div>
          )))}
          {status !== "over" && <div className={`g2048-tile g2048-active${active.value >= 512 ? " is-big" : ""}`} style={{ gridRow: active.row + 1, gridColumn: active.col + 1 }} aria-label={`Düşen taş ${active.value}`}><span>{active.value}</span></div>}
        </div>
        <aside className="g2048-next"><small>Sıradaki</small><b>{nextValue}</b><span>En yüksek taş {highest}</span></aside>
      </div>

      <div className="g2048-pad" role="group" aria-label="Taş kontrolleri">
        <button type="button" className="g2048-key is-left" onClick={() => control("left")} aria-label="Sola hareket et">←</button>
        <button type="button" className="g2048-key is-down" onClick={() => control("down")} aria-label="Aşağı indir">↓</button>
        <button type="button" className="g2048-key is-right" onClick={() => control("right")} aria-label="Sağa hareket et">→</button>
        <button type="button" className="g2048-drop" onClick={() => control("drop")}>Hızlı bırak</button>
      </div>

      <p className="memory-note" aria-live="polite">
        {status === "idle" ? <>Taşı sağa-sola yönlendir. Aynı komşu sayılar birleşir; <b>2048</b> hedefine ulaş. İlk tuşta 1 oyun hakkı kullanılır.</> :
          status === "playing" ? <>← → ile yönlendir, ↓ ile indir, boşlukla hızlı bırak. Aynı sayılar birleşip zincir oluşturur.</> : null}
      </p>
      {status === "won" && <div className="result is-ok"><b>Harika! 2048 hedefine ulaştın.</b><p>Skor için devam edebilir veya turun sonunda oyundan çıkabilirsin.</p><button type="button" className="btn btn-primary" onClick={() => { statusRef.current = "playing"; setStatus("playing"); }}>Devam et</button></div>}
      {status === "over" && <div className="result is-bad"><b>Yeni taş için yer kalmadı.</b><p>Skor: <b>{score}</b>. Sütunları dengeli kullanıp zincir birleşmeler oluşturmaya çalış.</p></div>}
      {status === "timeup" && <div className="result is-bad"><b>Bugünkü oyun süren doldu.</b><p>Skorun: <b>{score}</b>. Yeni oyun hakkın varsa daha sonra tekrar deneyebilirsin.</p></div>}

      <div className="sheet-actions">
        <button type="button" className="btn btn-primary btn-block" onClick={restart} disabled={!canRestart}>{canRestart ? "Yeni tur başlat (1 hak)" : "Yeni tur için hak/süre yok"}</button>
        <button type="button" className="btn btn-ghost btn-block" onClick={exit}>Geri dön</button>
      </div>
      <p className="privacy-notice" role="note">Oyun XP kazandırmaz; yalnızca çalışma hedefini tamamladıktan sonra kazandığın hakkı ve süreyi kullanır.</p>
    </div>
  );
}
