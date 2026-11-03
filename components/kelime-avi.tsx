"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { formatClock } from "./memory-game";

type WordEntry = { word: string; subject: string };
type Status = "ready" | "playing" | "over" | "timeup";
type Tile = { id: number; char: string };

const ROUND_SECONDS = 90;
const STARTING_LIVES = 3;

/** Müfredat konu adlarından kelime havuzu (8. sınıf LGS). */
const WORDS: WordEntry[] = [
  { word: "CÜMLE", subject: "Türkçe" },
  { word: "PARAGRAF", subject: "Türkçe" },
  { word: "YAZIM", subject: "Türkçe" },
  { word: "SÖZCÜK", subject: "Türkçe" },
  { word: "NESNE", subject: "Türkçe" },
  { word: "ÖZNE", subject: "Türkçe" },
  { word: "FİİL", subject: "Türkçe" },
  { word: "SIFAT", subject: "Türkçe" },
  { word: "ZARF", subject: "Türkçe" },
  { word: "ANLAM", subject: "Türkçe" },
  { word: "ÜÇGEN", subject: "Matematik" },
  { word: "DENKLEM", subject: "Matematik" },
  { word: "ÜS", subject: "Matematik" },
  { word: "ORAN", subject: "Matematik" },
  { word: "AÇI", subject: "Matematik" },
  { word: "KARE", subject: "Matematik" },
  { word: "DAİRE", subject: "Matematik" },
  { word: "OLASILIK", subject: "Matematik" },
  { word: "KÖK", subject: "Matematik" },
  { word: "HÜCRE", subject: "Fen Bilimleri" },
  { word: "MİTOZ", subject: "Fen Bilimleri" },
  { word: "ELEKTRİK", subject: "Fen Bilimleri" },
  { word: "KUVVET", subject: "Fen Bilimleri" },
  { word: "HIZ", subject: "Fen Bilimleri" },
  { word: "BASINÇ", subject: "Fen Bilimleri" },
  { word: "IŞIK", subject: "Fen Bilimleri" },
  { word: "SES", subject: "Fen Bilimleri" },
  { word: "ATOM", subject: "Fen Bilimleri" },
  { word: "CUMHURİYET", subject: "İnkılap Tarihi" },
  { word: "REFORM", subject: "İnkılap Tarihi" },
  { word: "ANAYASA", subject: "İnkılap Tarihi" },
  { word: "EGEMENLİK", subject: "İnkılap Tarihi" },
  { word: "LAİKLİK", subject: "İnkılap Tarihi" },
  { word: "İBADET", subject: "Din Kültürü" },
  { word: "ZEKÂT", subject: "Din Kültürü" },
  { word: "SADAKA", subject: "Din Kültürü" },
  { word: "ORUÇ", subject: "Din Kültürü" },
  { word: "NAMAZ", subject: "Din Kültürü" },
  { word: "AHLAK", subject: "Din Kültürü" },
  { word: "SABIR", subject: "Din Kültürü" },
  { word: "SCHOOL", subject: "İngilizce" },
  { word: "TEACHER", subject: "İngilizce" },
  { word: "FRIEND", subject: "İngilizce" },
  { word: "FAMILY", subject: "İngilizce" },
  { word: "WEATHER", subject: "İngilizce" },
  { word: "KITCHEN", subject: "İngilizce" },
];

function shuffle<T>(list: T[]): T[] {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function makeTiles(word: string): Tile[] {
  return shuffle([...word].map((char, id) => ({ id, char })));
}

export function KelimeAvi({
  rightsLeft,
  remainingSeconds,
  onRoundStart,
  onRoundEnd,
}: {
  rightsLeft: number;
  remainingSeconds: number;
  onRoundStart: () => void;
  onRoundEnd: (seconds: number) => void;
}) {
  const [status, setStatus] = useState<Status>("ready");
  const statusRef = useRef<Status>("ready");
  const [entry, setEntry] = useState<WordEntry | null>(null);
  const [pool, setPool] = useState<Tile[]>([]);
  const [picked, setPicked] = useState<Tile[]>([]);
  const [lives, setLives] = useState(STARTING_LIVES);
  const [score, setScore] = useState(0);
  const [streak, setStreak] = useState(0);
  const [answered, setAnswered] = useState(0);
  const [correctCount, setCorrectCount] = useState(0);
  const [verdict, setVerdict] = useState<"good" | "bad" | null>(null);
  const [seconds, setSeconds] = useState(Math.min(ROUND_SECONDS, Math.max(0, remainingSeconds)));

  const elapsedRef = useRef(0);
  const startedRef = useRef(false);
  const endedRef = useRef(false);
  const livesRef = useRef(STARTING_LIVES);
  const queueRef = useRef<WordEntry[]>([]);
  const pickedRef = useRef<Tile[]>([]);
  const advanceTimerRef = useRef<number | null>(null);
  const roundLimitRef = useRef(ROUND_SECONDS);

  const endRound = useCallback(() => {
    if (!startedRef.current || endedRef.current) return;
    endedRef.current = true;
    onRoundEnd(elapsedRef.current);
  }, [onRoundEnd]);

  const nextWord = useCallback(() => {
    if (queueRef.current.length === 0) queueRef.current = shuffle(WORDS);
    const word = queueRef.current.shift() ?? WORDS[0];
    pickedRef.current = [];
    setEntry(word);
    setPool(makeTiles(word.word));
    setPicked([]);
    setVerdict(null);
  }, []);

  const finish = useCallback(
    (result: "over" | "timeup") => {
      statusRef.current = result;
      setStatus(result);
      endRound();
    },
    [endRound]
  );

  const start = useCallback(() => {
    if (status !== "ready" || rightsLeft <= 0 || remainingSeconds <= 0) return;
    startedRef.current = true;
    statusRef.current = "playing";
    onRoundStart();
    roundLimitRef.current = Math.min(ROUND_SECONDS, remainingSeconds);
    setStatus("playing");
    setSeconds(roundLimitRef.current);
    queueRef.current = shuffle(WORDS);
    nextWord();
  }, [nextWord, onRoundStart, remainingSeconds, rightsLeft, status]);

  /** Tam oturan harflerden kelimeyi değerlendir. */
  const evaluate = useCallback(
    (candidate: Tile[]) => {
      if (!entry || statusRef.current !== "playing") return;
      const built = candidate.map((tile) => tile.char).join("");
      setAnswered((value) => value + 1);
      if (built === entry.word) {
        setScore((value) => value + 10);
        setStreak((value) => value + 1);
        setCorrectCount((value) => value + 1);
        setVerdict("good");
        advanceTimerRef.current = window.setTimeout(() => nextWord(), 850);
      } else {
        const nextLives = livesRef.current - 1;
        livesRef.current = nextLives;
        setLives(nextLives);
        setStreak(0);
        setVerdict("bad");
        advanceTimerRef.current = window.setTimeout(() => {
          if (nextLives <= 0) finish("over");
          else nextWord();
        }, 1150);
      }
    },
    [entry, finish, nextWord]
  );

  function pickTile(tile: Tile) {
    if (!entry || verdict || statusRef.current !== "playing") return;
    if (pickedRef.current.some((t) => t.id === tile.id)) return;
    const next = [...pickedRef.current, tile];
    pickedRef.current = next;
    setPool((value) => value.filter((t) => t.id !== tile.id));
    setPicked(next);
    if (next.length === entry.word.length) evaluate(next);
  }

  function returnTile(tile: Tile) {
    if (verdict || statusRef.current !== "playing") return;
    pickedRef.current = pickedRef.current.filter((t) => t.id !== tile.id);
    setPicked([...pickedRef.current]);
    setPool((value) => (value.some((t) => t.id === tile.id) ? value : [...value, tile]));
  }

  function clearPicked() {
    if (verdict || statusRef.current !== "playing") return;
    const back = pickedRef.current;
    pickedRef.current = [];
    setPool((value) => shuffle([...value, ...back]));
    setPicked([]);
  }

  function skipWord() {
    if (verdict || statusRef.current !== "playing") return;
    setStreak(0);
    nextWord();
  }

  useEffect(() => {
    if (status !== "playing") return;
    const timer = window.setInterval(() => {
      elapsedRef.current += 1;
      setSeconds((value) => Math.max(0, value - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [status]);

  useEffect(() => {
    if (status === "playing" && seconds <= 0) finish("timeup");
  }, [finish, seconds, status]);

  useEffect(
    () => () => {
      if (advanceTimerRef.current !== null) window.clearTimeout(advanceTimerRef.current);
      endRound();
    },
    [endRound]
  );

  return (
    <div className="kelime-avi">
      <div className="kelime-hud" aria-label="Tur bilgileri">
        <div>
          <small>Puan</small>
          <b>{score}</b>
        </div>
        <div>
          <small>Can</small>
          <b aria-label={`${lives} can`}>
            {"❤️".repeat(lives)}
            {"🖤".repeat(STARTING_LIVES - lives)}
          </b>
        </div>
        <div>
          <small>Süre</small>
          <b>{formatClock(seconds)}</b>
        </div>
        <div>
          <small>Seri</small>
          <b>{streak}</b>
        </div>
      </div>

      {status === "ready" ? (
        <div className="kelime-start">
          <h4>Hazır mısın?</h4>
          <p>
            Karışık harfleri sıralayarak konu kelimesini bul. Yanlış tahminde bir canın gider;
            istersen pas geçebilirsin. 3 can ve 90 saniyen var.
          </p>
          <button
            className="btn btn-primary"
            type="button"
            onClick={start}
            disabled={rightsLeft <= 0 || remainingSeconds <= 0}
          >
            Oyuna başla
          </button>
        </div>
      ) : status === "playing" && entry ? (
        <section aria-live="polite">
          <div className="kelime-hint">
            <span>📘 {entry.subject}</span>
            <span>🔤 {entry.word.length} harf</span>
            {streak >= 2 && <span>🔥 {streak} seri</span>}
          </div>

          <div className="kelime-slots" style={{ margin: "12px 0" }}>
            {entry.word.split("").map((_, index) => {
              const tile = picked[index];
              return (
                <button
                  type="button"
                  key={index}
                  className={`kelime-slot${tile ? " is-filled" : ""}`}
                  onClick={() => tile && returnTile(tile)}
                  aria-label={tile ? `${tile.char} harfini geri al` : "boş kutu"}
                >
                  {tile?.char ?? ""}
                </button>
              );
            })}
          </div>

          <div className="kelime-tiles">
            {pool.map((tile) => (
              <button
                type="button"
                key={tile.id}
                className="kelime-tile"
                onClick={() => pickTile(tile)}
                disabled={Boolean(verdict)}
              >
                {tile.char}
              </button>
            ))}
          </div>

          <div className="kelime-toolbar" style={{ marginTop: 12 }}>
            <button type="button" className="btn btn-soft" onClick={clearPicked} disabled={Boolean(verdict) || picked.length === 0}>
              Temizle
            </button>
            <button type="button" className="btn btn-soft" onClick={skipWord} disabled={Boolean(verdict)}>
              Pas geç
            </button>
          </div>

          {verdict && (
            <p className={`kelime-verdict ${verdict === "good" ? "is-good" : "is-bad"}`} style={{ marginTop: 12 }}>
              {verdict === "good"
                ? "Doğru! 🎉 Sıradaki kelime geliyor…"
                : `Olmadı — doğru kelime: ${entry.word}. ${lives} canın kaldı.`}
            </p>
          )}
        </section>
      ) : (
        <div className="kelime-result" role="status">
          <span aria-hidden="true">{status === "timeup" ? "⏱️" : lives <= 0 ? "💪" : "🏁"}</span>
          <h4>{status === "timeup" ? "Süre tamamlandı!" : lives <= 0 ? "Oyun bitti" : "Güzel bir turdu!"}</h4>
          <p>
            {answered} denemede {correctCount} doğru kelime · {score} puan
          </p>
          <p>
            {status === "timeup"
              ? `${roundLimitRef.current} saniyelik turun bitti.`
              : lives <= 0
                ? "Canların bitti. Biraz dinlenip yeniden deneyebilirsin."
                : "Günlük oyun süren sona erdi."}
          </p>
        </div>
      )}
      <p className="kelime-disclaimer">
        Kelimeler LGS müfredatındaki konu adlarından seçilir; resmi LGS sorusu değildir.
      </p>
    </div>
  );
}