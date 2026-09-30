"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Grid = number[][];
type Status = "idle" | "playing" | "won" | "over" | "timeup";
type ActiveTile = { row: number; col: number; value: number };
type Control = "left" | "right" | "down" | "drop";

const ROWS = 8;
const COLS = 5;
const WIN_TILE = 2048;
const GRAVITY_MS = 850;
const CENTER_COL = Math.floor(COLS / 2);

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

type Cell = { row: number; col: number };

function settle(grid: Grid, anchor?: Cell): { grid: Grid; anchor: Cell | null } {
  const next = emptyGrid();
  let nextAnchor: Cell | null = null;
  for (let col = 0; col < COLS; col += 1) {
    const values = grid.flatMap((row, rowIndex) => row[col] ? [{ value: row[col], row: rowIndex }] : []);
    const offset = ROWS - values.length;
    values.forEach(({ value, row }, index) => {
      next[offset + index][col] = value;
      if (anchor && anchor.col === col && anchor.row === row) nextAnchor = { row: offset + index, col };
    });
  }
  return { grid: next, anchor: nextAnchor };
}

function connectedGroup(grid: Grid, start: Cell): Cell[] {
  const value = grid[start.row]?.[start.col] ?? 0;
  if (!value) return [];
  const group: Cell[] = [];
  const queue: Cell[] = [start];
  const seen = new Set<string>();
  while (queue.length) {
    const cell = queue.pop()!;
    const key = `${cell.row}:${cell.col}`;
    if (seen.has(key) || grid[cell.row]?.[cell.col] !== value) continue;
    seen.add(key);
    group.push(cell);
    for (const [row, col] of [[cell.row - 1, cell.col], [cell.row + 1, cell.col], [cell.row, cell.col - 1], [cell.row, cell.col + 1]]) {
      if (row >= 0 && row < ROWS && col >= 0 && col < COLS) queue.push({ row, col });
    }
  }
  return group;
}

function findMergeGroup(grid: Grid): Cell[] | null {
  for (let row = ROWS - 1; row >= 0; row -= 1) {
    for (let col = 0; col < COLS; col += 1) {
      if (!grid[row][col]) continue;
      const group = connectedGroup(grid, { row, col });
      if (group.length > 1) return group;
    }
  }
  return null;
}

/** Merge a matching cluster into one doubled tile, then settle for cascades. */
function mergeCascade(source: Grid, landing: Cell): { grid: Grid; score: number; highest: number; multipliers: number[] } {
  let grid = source.map((row) => [...row]);
  let anchor: Cell = landing;
  let score = 0;
  let highest = Math.max(...grid.flat());
  const multipliers: number[] = [];
  let group = connectedGroup(grid, anchor);
  for (;;) {
    if (group.length < 2) group = findMergeGroup(grid) ?? [];
    if (group.length < 2) break;
    const keep = group.some((cell) => cell.row === anchor.row && cell.col === anchor.col) ? anchor : group[0];
    const value = grid[group[0].row][group[0].col];
    const multiplier = 2 ** (group.length - 1);
    const merged = value * multiplier;
    const next = grid.map((line) => [...line]);
    for (const cell of group) next[cell.row][cell.col] = 0;
    next[keep.row][keep.col] = merged;
    score += merged;
    highest = Math.max(highest, merged);
    multipliers.push(multiplier);
    const settled = settle(next, keep);
    grid = settled.grid;
    anchor = settled.anchor ?? keep;
    group = connectedGroup(grid, anchor);
  }
  return { grid, score, highest, multipliers };
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
  const [active, setActive] = useState<ActiveTile>({ row: 0, col: CENTER_COL, value: randomTile() });
  const [nextValues, setNextValues] = useState<[number, number]>(() => [randomTile(), randomTile()]);
  const [heldValue, setHeldValue] = useState<number | null>(null);
  const [canHold, setCanHold] = useState(true);
  const [score, setScore] = useState(0);
  const [best, setBest] = useState(0);
  const [drops, setDrops] = useState(0);
  const [mergeNotice, setMergeNotice] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [timeLeft, setTimeLeft] = useState(Math.max(0, remainingSeconds));

  const elapsedRef = useRef(0);
  const endedRef = useRef(false);
  const startedRef = useRef(false);
  const gridRef = useRef(grid);
  const activeRef = useRef(active);
  const statusRef = useRef(status);
  const endRoundRef = useRef(onRoundEnd);
  const softDropTimerRef = useRef<number | null>(null);
  const softDropPointerRef = useRef(false);
  const softDropKeyBlockedRef = useRef(false);
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

  const findSpawnColumn = useCallback((board: Grid): number | null => {
    const columns = Array.from({ length: COLS }, (_, col) => col)
      .sort((a, b) => Math.abs(a - CENTER_COL) - Math.abs(b - CENTER_COL));
    return columns.find((col) => board[0][col] === 0) ?? null;
  }, []);

  const lockTile = useCallback((tile: ActiveTile) => {
    const board = gridRef.current.map((row) => [...row]);
    if (tile.row < 0 || tile.row >= ROWS || tile.col < 0 || tile.col >= COLS) {
      statusRef.current = "over";
      setStatus("over");
      return;
    }
    let landing = tile;
    if (board[landing.row][landing.col] !== 0) {
      let safeRow = landing.row - 1;
      while (safeRow >= 0 && board[safeRow][landing.col] !== 0) safeRow -= 1;
      if (safeRow < 0) {
        statusRef.current = "over";
        setStatus("over");
        return;
      }
      landing = { ...landing, row: safeRow };
    }
    board[landing.row][landing.col] = landing.value;
    const resolved = mergeCascade(board, { row: landing.row, col: landing.col });
    gridRef.current = resolved.grid;
    setGrid(resolved.grid);
    setScore((current) => {
      const updated = current + resolved.score;
      setBest((previous) => Math.max(previous, updated));
      return updated;
    });
    setDrops((current) => current + 1);
    setMergeNotice(resolved.multipliers.length
      ? resolved.multipliers.map((multiplier) => `×${multiplier}`).join(" zincir · ") + " birleşme"
      : "");
    const nextActiveValue = nextValues[0];
    setNextValues([nextValues[1], randomTile()]);
    setCanHold(true);
    if (resolved.highest >= WIN_TILE) {
      const spawnCol = findSpawnColumn(resolved.grid) ?? CENTER_COL;
      const nextActive = { row: 0, col: spawnCol, value: nextActiveValue };
      setActive(nextActive);
      activeRef.current = nextActive;
      statusRef.current = "won";
      setStatus("won");
      return;
    }
    const spawnCol = findSpawnColumn(resolved.grid);
    if (spawnCol === null) {
      statusRef.current = "over";
      setStatus("over");
      return;
    }
    const nextActive = { row: 0, col: spawnCol, value: nextActiveValue };
    setActive(nextActive);
    activeRef.current = nextActive;
  }, [findSpawnColumn, nextValues]);

  const control = useCallback((action: Control): boolean => {
    const currentStatus = statusRef.current;
    if (currentStatus !== "idle" && currentStatus !== "playing") return false;
    if (currentStatus === "idle") begin();
    const tile = activeRef.current;
    if (action === "left" || action === "right") {
      const col = tile.col + (action === "left" ? -1 : 1);
      if (col >= 0 && col < COLS && gridRef.current[tile.row][col] === 0) {
        const moved = { ...tile, col };
        activeRef.current = moved;
        setActive(moved);
      }
      return true;
    }
    if (action === "drop") {
      let row = tile.row;
      while (row + 1 < ROWS && gridRef.current[row + 1][tile.col] === 0) row += 1;
      lockTile({ ...tile, row });
      return false;
    }
    const nextRow = tile.row + 1;
    if (nextRow < ROWS && gridRef.current[nextRow][tile.col] === 0) {
      const moved = { ...tile, row: nextRow };
      activeRef.current = moved;
      setActive(moved);
      return true;
    } else {
      lockTile(tile);
      return false;
    }
  }, [begin, lockTile]);

  function stopSoftDrop() {
    if (softDropTimerRef.current !== null) {
      window.clearInterval(softDropTimerRef.current);
      softDropTimerRef.current = null;
    }
  }

  function startSoftDrop() {
    softDropPointerRef.current = true;
    stopSoftDrop();
    if (!control("down")) return;
    softDropTimerRef.current = window.setInterval(() => {
      if (!control("down")) stopSoftDrop();
    }, 90);
  }

  function handleSoftDropClick() {
    if (softDropPointerRef.current) {
      softDropPointerRef.current = false;
      return;
    }
    control("down");
  }

  useEffect(() => () => stopSoftDrop(), []);

  function holdCurrent() {
    if (!canHold || (statusRef.current !== "idle" && statusRef.current !== "playing")) return;
    if (statusRef.current === "idle") begin();
    const current = activeRef.current;
    if (heldValue === null) {
      const col = findSpawnColumn(gridRef.current);
      if (col === null) return;
      setHeldValue(current.value);
      const replacement = { row: 0, col, value: nextValues[0] };
      setActive(replacement);
      activeRef.current = replacement;
      setNextValues([nextValues[1], randomTile()]);
    } else {
      setHeldValue(current.value);
      const replacement = { ...current, value: heldValue };
      setActive(replacement);
      activeRef.current = replacement;
    }
    setCanHold(false);
  }

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
      if (key === "c") {
        event.preventDefault();
        holdCurrent();
        return;
      }
      if (!action) return;
      if (action === "down" && softDropKeyBlockedRef.current) return;
      event.preventDefault();
      const canContinue = control(action);
      if (action === "down" && !canContinue) softDropKeyBlockedRef.current = true;
    }
    function onKeyUp(event: KeyboardEvent) {
      if (event.key.toLowerCase() === "arrowdown" || event.key.toLowerCase() === "s") {
        softDropKeyBlockedRef.current = false;
      }
    }
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("keyup", onKeyUp);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("keyup", onKeyUp);
    };
  }, [control, holdCurrent]);

  function restart() {
    endRound();
    endedRef.current = false;
    startedRef.current = false;
    elapsedRef.current = 0;
    const fresh = emptyGrid();
    gridRef.current = fresh;
    setGrid(fresh);
    const first = randomTile();
    setActive({ row: 0, col: CENTER_COL, value: first });
    activeRef.current = { row: 0, col: CENTER_COL, value: first };
    setNextValues([randomTile(), randomTile()]);
    setHeldValue(null);
    setCanHold(true);
    setScore(0);
    setBest(0);
    setDrops(0);
    setMergeNotice("");
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
  const level = Math.floor(drops / 10) + 1;

  return (
    <div className="g2048">
      <div className="game-hud">
        <div><small>Skor</small><b>{score}</b></div>
        <div><small>En iyi</small><b>{best}</b></div>
        <div><small>Düşüş</small><b>{drops}</b></div>
        <div><small>Seviye</small><b>{level}</b></div>
        <div><small>Kalan süre</small><b>{formatClock(timeLeft)}</b></div>
      </div>

      <div className="g2048-stage">
        <div className="g2048-board" role="grid" aria-label="Matematik 2048, 5 sütun ve 8 satır">
          {grid.map((row, r) => row.map((value, c) => (
            <div className={`g2048-tile${value ? "" : " is-empty"}${value >= 512 ? " is-big" : ""}`} role="gridcell" aria-label={value ? String(value) : "Boş"} key={`${r}-${c}`}>
              {value ? <span>{value}</span> : null}
            </div>
          )))}
          {status !== "over" && <div className={`g2048-tile g2048-active${active.value >= 512 ? " is-big" : ""}`} style={{ gridRow: active.row + 1, gridColumn: active.col + 1 }} aria-label={`Düşen taş ${active.value}`}><span>{active.value}</span></div>}
        </div>
        <aside className="g2048-side">
          <div className="g2048-preview">
            <small>Tut</small>
            <b className={heldValue === null ? "is-empty" : ""}>{heldValue ?? "—"}</b>
            <button type="button" onClick={holdCurrent} disabled={!canHold || (status !== "idle" && status !== "playing")}>Taşı tut <kbd>C</kbd></button>
          </div>
          <div className="g2048-preview">
            <small>Sıradaki</small>
            <div className="g2048-next-tiles">{nextValues.map((value, index) => <b key={index}>{value}</b>)}</div>
          </div>
          <span className="g2048-highest">En yüksek taş {highest}</span>
        </aside>
      </div>

      <div className="g2048-pad" role="group" aria-label="Taş kontrolleri">
        <button type="button" className="g2048-key is-left" onClick={() => control("left")} aria-label="Sola hareket et">←</button>
        <button
          type="button"
          className="g2048-key is-down"
          onPointerDown={startSoftDrop}
          onPointerUp={stopSoftDrop}
          onPointerCancel={() => { stopSoftDrop(); softDropPointerRef.current = false; }}
          onLostPointerCapture={stopSoftDrop}
          onClick={handleSoftDropClick}
          aria-label="Tek basışta bir kare indir, basılı tutarak hızlandır"
        >↓</button>
        <button type="button" className="g2048-key is-right" onClick={() => control("right")} aria-label="Sağa hareket et">→</button>
        <button type="button" className="g2048-drop" onClick={() => control("drop")}>Hızlı bırak</button>
      </div>

      <p className="memory-note" aria-live="polite">
        {mergeNotice ? <b>{mergeNotice}</b> : null}{mergeNotice ? " · " : ""}
        {status === "idle" ? <>Taşı sağa-sola yönlendir; ↓ tek basışta bir kare indirir, basılı tutunca hızlandırır. Aynı sayıları yan yana getirip zincir birleşmeleri oluştur. İlk tuşta 1 oyun hakkı kullanılır.</> :
          status === "playing" ? <>← → hareket, ↓ bir kare indirir, boşluk hızlı bırakır, C taşı tutar. Eşleşen 2/3/4 taş ×2/×4/×8 birleşir.</> : null}
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
