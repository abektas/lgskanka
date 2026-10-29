"use client";

import { useEffect, useRef, useState } from "react";

interface ExamTimerProps {
  durationMinutes: number;
  onTimeEnd: () => void;
  autoStart?: boolean;
}

export function ExamTimer({
  durationMinutes,
  onTimeEnd,
  autoStart = true,
}: ExamTimerProps) {
  const [timeLeft, setTimeLeft] = useState(durationMinutes * 60);
  const [isRunning, setIsRunning] = useState(autoStart);
  const [isPaused, setIsPaused] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number>(Date.now());
  const pausedDurationRef = useRef<number>(0);

  useEffect(() => {
    if (isRunning && !isPaused) {
      intervalRef.current = setInterval(() => {
        setTimeLeft((prev) => {
          if (prev <= 1) {
            if (intervalRef.current) clearInterval(intervalRef.current);
            onTimeEnd();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isRunning, isPaused, onTimeEnd]);

  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return h > 0
      ? `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
      : `${m}:${s.toString().padStart(2, "0")}`;
  };

  const progress = (durationMinutes * 60 - timeLeft) / (durationMinutes * 60);

  const togglePause = () => {
    setIsPaused((prev) => !prev);
    if (!isPaused) {
      pausedDurationRef.current += Date.now() - startTimeRef.current;
    } else {
      startTimeRef.current = Date.now();
    }
  };

  const reset = () => {
    setTimeLeft(durationMinutes * 60);
    setIsRunning(true);
    setIsPaused(false);
    startTimeRef.current = Date.now();
    pausedDurationRef.current = 0;
  };

  const warning = timeLeft <= 15 * 60; // son 15 dk
  const danger = timeLeft <= 5 * 60; // son 5 dk

  return (
    <div className="exam-timer" data-testid="exam-timer">
      <div
        className={`timer-display ${warning ? "warning" : ""} ${danger ? "danger" : ""}`}
        role="timer"
        aria-live={danger ? "assertive" : "polite"}
      >
        {formatTime(timeLeft)}
      </div>
      <div className="timer-progress" role="progressbar" aria-valuenow={Math.round(progress * 100)} aria-valuemin={0} aria-valuemax={100}>
        <i style={{ width: `${progress * 100}%` }} />
      </div>
      <div className="timer-controls">
        <button
          className="btn btn-soft"
          onClick={togglePause}
          disabled={timeLeft <= 0}
          aria-label={isPaused ? "Devam et" : "Duraklat"}
        >
          {isPaused ? "▶ Devam" : "⏸ Duraklat"}
        </button>
        <button className="btn btn-soft" onClick={reset} disabled={timeLeft === durationMinutes * 60}>
          ↻ Sıfırla
        </button>
      </div>
      <small className="timer-hint">
        {isPaused ? "⏸ Duraklatıldı" : danger ? "⚠ Son 5 dakika!" : warning ? "⚠ Son 15 dakika" : "⏱ Süre devam ediyor"}
      </small>
    </div>
  );
}

export default ExamTimer;