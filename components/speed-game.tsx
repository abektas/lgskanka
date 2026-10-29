"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { formatClock } from "./memory-game";

type SpeedQuestion = {
  id: string;
  subject: string;
  topic: string;
  text: string;
  options: string[];
  correctIndex: number;
};

type Status = "ready" | "playing" | "over" | "timeup";

const ROUND_SECONDS = 30;
const MAX_QUESTIONS = 20;

export function SpeedGame({
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
  const [questions, setQuestions] = useState<SpeedQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [score, setScore] = useState(0);
  const [streak, setStreak] = useState(0);
  const [seconds, setSeconds] = useState(Math.min(ROUND_SECONDS, Math.max(0, remainingSeconds)));
  const [feedback, setFeedback] = useState<{ selected: number; correct: boolean; correctIndex: number; explanation: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [answered, setAnswered] = useState(0);
  const elapsedRef = useRef(0);
  const startedRef = useRef(false);
  const endedRef = useRef(false);
  const advanceTimerRef = useRef<number | null>(null);
  const seenRef = useRef<string[]>([]);

  const endRound = useCallback(() => {
    if (!startedRef.current || endedRef.current) return;
    endedRef.current = true;
    onRoundEnd(elapsedRef.current);
  }, [onRoundEnd]);

  const loadQuestions = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/games/speed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "batch", count: MAX_QUESTIONS, exclude: seenRef.current }),
      });
      const data = await response.json();
      if (!response.ok || !data.questions) throw new Error(data.error ?? "Sorular yüklenemedi.");
      setQuestions(data.questions);
      seenRef.current = [...seenRef.current, ...data.questions.map((q: SpeedQuestion) => q.id)];
      setBusy(false);
    } catch {
      setError("Sorular yüklenemedi. Yeniden deneyebilirsin.");
      setBusy(false);
    }
  }, []);

  const finish = useCallback((result: "over" | "timeup") => {
    statusRef.current = result;
    setStatus(result);
    setBusy(false);
    endRound();
  }, [endRound]);

  const start = useCallback(async () => {
    if (status !== "ready" || rightsLeft <= 0 || remainingSeconds <= 0) return;
    startedRef.current = true;
    statusRef.current = "playing";
    onRoundStart();
    setSeconds(Math.min(ROUND_SECONDS, remainingSeconds));
    setStatus("playing");
    await loadQuestions();
  }, [loadQuestions, onRoundStart, remainingSeconds, rightsLeft, status]);

  async function choose(index: number) {
    if (!questions[currentIndex] || busy || status !== "playing" || feedback) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/games/speed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "answer", questionId: questions[currentIndex].id, selectedIndex: index }),
      });
      const result = await response.json();
      if (statusRef.current !== "playing") return;
      if (!response.ok) throw new Error(result.error ?? "Cevap değerlendirilemedi.");
      const correct = result.correct;
      setFeedback({ selected: index, correct, correctIndex: result.correctIndex, explanation: result.explanation });
      setAnswered((value) => value + 1);
      if (correct) {
        setScore((value) => value + 10);
        setStreak((value) => value + 1);
      } else {
        setStreak(0);
      }
      advanceTimerRef.current = window.setTimeout(() => {
        setFeedback(null);
        if (currentIndex < MAX_QUESTIONS - 1) {
          setCurrentIndex((prev) => prev + 1);
        } else {
          finish("over");
        }
      }, 900);
    } catch {
      setError("Cevabın değerlendirilemedi. Tekrar deneyebilirsin.");
      setBusy(false);
    }
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

  useEffect(() => () => {
    if (advanceTimerRef.current !== null) window.clearTimeout(advanceTimerRef.current);
    endRound();
  }, [endRound]);

  const canRestart = rightsLeft > 0 && remainingSeconds > 0;

  return (
    <div className="speed-game">
      <div className="speed-hud" aria-label="Tur bilgileri">
        <div><small>Puan</small><b>{score}</b></div>
        <div><small>Seri</small><b>{streak}</b></div>
        <div><small>Süre</small><b>{formatClock(seconds)}</b></div>
        <div><small>Cevaplanan</small><b>{answered}/{MAX_QUESTIONS}</b></div>
      </div>

      {status === "ready" && (
        <div className="speed-start">
          <h4>Hız Oyunu — 30 Saniye</h4>
          <p>30 saniyede mümkün olduğunca çok doğru cevap ver. Hız kadar doğruluk da puanlanır.</p>
          <button className="btn btn-primary" type="button" onClick={start} disabled={rightsLeft <= 0 || remainingSeconds <= 0}>
            Oyuna Başla
          </button>
        </div>
      )}

      {status === "playing" && (
        <section className="speed-question" aria-live="polite">
          {questions[currentIndex] ? (
            <>
              <div className="speed-topic">
                <span>{questions[currentIndex].subject}</span>
                <span>{questions[currentIndex].topic}</span>
              </div>
              <h4>{questions[currentIndex].text}</h4>
              <div className="speed-options">
                {questions[currentIndex].options.map((option, index) => {
                  const selected = feedback?.selected === index;
                  const correct = feedback?.correctIndex === index;
                  const stateClass = feedback ? correct ? "is-correct" : selected ? "is-wrong" : "" : "";
                  return (
                    <button
                      type="button"
                      key={`${questions[currentIndex].id}-${index}`}
                      className={`speed-option ${stateClass}`}
                      disabled={busy || Boolean(feedback)}
                      onClick={() => choose(index)}
                    >
                      <span>{String.fromCharCode(65 + index)}</span>{option}
                    </button>
                  );
                })}
              </div>
              {feedback && (
                <p className={`speed-feedback ${feedback.correct ? "is-good" : "is-bad"}`}>
                  {feedback.correct ? "Doğru! ⚡" : "Yanlış, doğru cevap yeşil."} {feedback.explanation}
                </p>
              )}
            </>
          ) : (
            <p className="speed-loading">{error || "Sorular hazırlanıyor…"}</p>
          )}
          {error && <p className="speed-error" role="alert">{error} <button type="button" onClick={loadQuestions}>Yeniden dene</button></p>}
        </section>
      )}

      {status === "over" || status === "timeup" && (
        <div className="speed-result" role="status">
          <span aria-hidden="true">{status === "timeup" ? "⏱️" : "🏁"}</span>
          <h4>{status === "timeup" ? "Süre Doldu!" : "Tur Tamamlandı!"}</h4>
          <p>{answered} soruda {score / 10} doğru · {score} puan</p>
          <p>{status === "timeup" ? `${ROUND_SECONDS} saniyelik tur bitti.` : "Harika bir turdu!"}</p>
        </div>
      )}

      <p className="speed-disclaimer">Hız Oyunu eğitim amaçlıdır; resmi sınav sorusu değildir.</p>

      <div className="sheet-actions">
        <button type="button" className="btn btn-primary btn-block" onClick={() => { setCurrentIndex(0); setScore(0); setStreak(0); setAnswered(0); setFeedback(null); start(); }} disabled={!canRestart}>
          {canRestart ? "Yeniden Oyna (1 hak)" : "Yeniden oynamak için hak/süre yok"}
        </button>
        <button type="button" className="btn btn-ghost btn-block" onClick={() => { setCurrentIndex(0); setScore(0); setStreak(0); setAnswered(0); setFeedback(null); setStatus("ready"); endedRef.current = false; }}>Geri Dön</button>
      </div>

      <p className="privacy-notice" role="note">Hız Oyunu XP kazandırmaz; yalnızca çalışma hedefini tamamladıktan sonra kazandığın hakkı ve süreyi kullanır.</p>
    </div>
  );
}