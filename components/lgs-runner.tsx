"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { formatClock } from "./memory-game";

type RunnerQuestion = {
  id: string;
  subject: string;
  topic: string;
  text: string;
  options: string[];
};
type Status = "ready" | "playing" | "over" | "timeup";
type Feedback = { selected: number; correct: boolean; correctIndex: number; explanation: string } | null;

const ROUND_SECONDS = 90;
const STARTING_LIVES = 3;

export function LgsRunner({
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
  const roundLimitRef = useRef(ROUND_SECONDS);
  const [question, setQuestion] = useState<RunnerQuestion | null>(null);
  const [lives, setLives] = useState(STARTING_LIVES);
  const [score, setScore] = useState(0);
  const [streak, setStreak] = useState(0);
  const [seconds, setSeconds] = useState(Math.min(ROUND_SECONDS, Math.max(0, remainingSeconds)));
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [motion, setMotion] = useState<"run" | "jump" | "hit">("run");
  const [answered, setAnswered] = useState(0);
  const elapsedRef = useRef(0);
  const startedRef = useRef(false);
  const endedRef = useRef(false);
  const seenRef = useRef<string[]>([]);
  const advanceTimerRef = useRef<number | null>(null);

  const endRound = useCallback(() => {
    if (!startedRef.current || endedRef.current) return;
    endedRef.current = true;
    onRoundEnd(elapsedRef.current);
  }, [onRoundEnd]);

  const loadQuestion = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/games/runner", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "next", exclude: seenRef.current }),
      });
      const data = await response.json();
      if (!response.ok || !data.question) throw new Error(data.error ?? "Soru yüklenemedi.");
      setQuestion(data.question as RunnerQuestion);
      seenRef.current = [...seenRef.current, data.question.id];
      if (seenRef.current.length >= 3) seenRef.current = [];
      setFeedback(null);
      setBusy(false);
    } catch {
      setError("Soru yüklenemedi. Yeniden deneyebilirsin.");
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
    roundLimitRef.current = Math.min(ROUND_SECONDS, remainingSeconds);
    setStatus("playing");
    setSeconds(roundLimitRef.current);
    await loadQuestion();
  }, [loadQuestion, onRoundStart, remainingSeconds, rightsLeft, status]);

  async function choose(index: number) {
    if (!question || busy || status !== "playing" || feedback) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/games/runner", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "answer", questionId: question.id, selectedIndex: index }),
      });
      const result = await response.json();
      if (statusRef.current !== "playing") return;
      if (!response.ok) throw new Error(result.error ?? "Cevap değerlendirilemedi.");
      const answer: Feedback = { selected: index, correct: result.correct, correctIndex: result.correctIndex, explanation: result.explanation };
      setFeedback(answer);
      setAnswered((value) => value + 1);
      if (result.correct) {
        setScore((value) => value + 10);
        setStreak((value) => value + 1);
        setMotion("jump");
      } else {
        setLives((value) => value - 1);
        setStreak(0);
        setMotion("hit");
      }
      const lifeCountAfterAnswer = result.correct ? lives : lives - 1;
      if (lifeCountAfterAnswer <= 0) {
        advanceTimerRef.current = window.setTimeout(() => finish("over"), 1500);
      } else {
        advanceTimerRef.current = window.setTimeout(() => {
          setMotion("run");
          loadQuestion();
        }, 1400);
      }
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

  return (
    <div className="lgs-runner">
      <div className="runner-hud" aria-label="Tur bilgileri">
        <div><small>Puan</small><b>{score}</b></div>
        <div><small>Can</small><b aria-label={`${lives} can`}>{"❤️".repeat(lives)}{"🖤".repeat(STARTING_LIVES - lives)}</b></div>
        <div><small>Süre</small><b>{formatClock(seconds)}</b></div>
        <div><small>Seri</small><b>{streak}</b></div>
      </div>

      <div className={`runner-track is-${motion}`} aria-label="Koşu parkuru">
        <span className="runner-cloud runner-cloud-one" aria-hidden="true">☁️</span>
        <span className="runner-cloud runner-cloud-two" aria-hidden="true">☁️</span>
        <span className="runner-distance" aria-hidden="true">{score / 10} engel aşıldı</span>
        <span className="runner-character" aria-hidden="true">🏃‍♂️</span>
        <span className="runner-obstacle" aria-hidden="true">🪨</span>
        <span className="runner-ground" aria-hidden="true" />
      </div>

      {status === "ready" ? (
        <div className="runner-start">
          <h4>Hazır mısın?</h4>
          <p>Doğru yanıtla engelleri aş. Yanlış cevapta bir canın gider; 3 can ve 90 saniyen var.</p>
          <button className="btn btn-primary" type="button" onClick={start} disabled={rightsLeft <= 0 || remainingSeconds <= 0}>Koşuya başla</button>
        </div>
      ) : status === "playing" ? (
        <section className="runner-question" aria-live="polite">
          {question ? <>
            <div className="runner-topic"><span>{question.subject}</span><span>{question.topic}</span></div>
            <h4>{question.text}</h4>
            <div className="runner-options">
              {question.options.map((option, index) => {
                const selected = feedback?.selected === index;
                const correct = feedback?.correctIndex === index;
                const stateClass = feedback ? correct ? "is-correct" : selected ? "is-wrong" : "" : "";
                return <button type="button" key={`${question.id}-${index}`} className={`runner-option ${stateClass}`} disabled={busy || Boolean(feedback)} onClick={() => choose(index)}>
                  <span>{String.fromCharCode(65 + index)}</span>{option}
                </button>;
              })}
            </div>
            {feedback && <p className={`runner-feedback ${feedback.correct ? "is-good" : "is-bad"}`}>{feedback.correct ? "Harika, engeli aştın!" : "Bu kez olmadı; doğru yanıt yeşil renkle gösterildi."} {feedback.explanation}</p>}
          </> : <p className="runner-loading">{error || "Soru hazırlanıyor…"}</p>}
          {error && <p className="runner-error" role="alert">{error} <button type="button" onClick={loadQuestion}>Yeniden dene</button></p>}
        </section>
      ) : (
        <div className="runner-result" role="status">
          <span aria-hidden="true">{status === "timeup" ? "⏱️" : lives <= 0 ? "💪" : "🏁"}</span>
          <h4>{status === "timeup" ? "Süre tamamlandı!" : lives <= 0 ? "Koşu sona erdi" : "Güzel bir turdu!"}</h4>
          <p>{answered} soruda {score / 10} doğru cevap · {score} puan</p>
          <p>{status === "timeup" ? "{roundLimitRef.current} saniyelik turun bitti." : lives <= 0 ? "Canların bitti. Biraz dinlenip yeniden deneyebilirsin." : "Günlük oyun süren sona erdi."}</p>
        </div>
      )}
      <p className="runner-disclaimer">Alıştırmalar uygulamanın örnek soru havuzundan gelir; resmi LGS sorusu değildir.</p>
    </div>
  );
}
