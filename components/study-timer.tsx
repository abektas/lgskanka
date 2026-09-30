"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { subjects } from "../data/content";

const STORAGE_KEY = "lgs-ai-coach-pomodoro-v1";
const FOCUS_SECONDS = 25 * 60;
const SHORT_BREAK_SECONDS = 5 * 60;
const LONG_BREAK_SECONDS = 15 * 60;
const studySubjects = [
  ...subjects,
  { slug: "inkilap", name: "T.C. İnkılap Tarihi" },
  { slug: "din", name: "Din Kültürü ve Ahlak Bilgisi" },
];

type Phase = "focus" | "short-break" | "long-break";
type TimerStatus = "ready" | "running" | "paused";
type DailyStats = {
  day: string;
  focusSessions: number;
  focusMinutes: number;
  bySubject: Record<string, number>;
};

function todayKey(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function emptyStats(): DailyStats {
  return { day: todayKey(), focusSessions: 0, focusMinutes: 0, bySubject: {} };
}

function formatClock(totalSeconds: number): string {
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function isSubjectSlug(value: unknown): value is string {
  return typeof value === "string" && studySubjects.some((subject) => subject.slug === value);
}

function readStoredState(): {
  stats: DailyStats;
  phase: Phase;
  status: TimerStatus;
  remainingSeconds: number;
  selectedSubject: string;
  sessionSubject: string | null;
  endsAt: number | null;
} | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    const value = parsed as Record<string, unknown>;
    if (!value.stats || typeof value.stats !== "object") return null;
    const rawStats = value.stats as Record<string, unknown>;
    if (rawStats.day !== todayKey()) return null;
    const phase = value.phase;
    const status = value.status;
    if (phase !== "focus" && phase !== "short-break" && phase !== "long-break") return null;
    if (status !== "ready" && status !== "running" && status !== "paused") return null;
    const bySubject: Record<string, number> = {};
    if (rawStats.bySubject && typeof rawStats.bySubject === "object") {
      for (const [slug, minutes] of Object.entries(rawStats.bySubject)) {
        if (isSubjectSlug(slug) && typeof minutes === "number" && Number.isFinite(minutes) && minutes > 0) {
          bySubject[slug] = Math.min(24 * 60, Math.floor(minutes));
        }
      }
    }
    const selectedSubject = isSubjectSlug(value.selectedSubject) ? value.selectedSubject : studySubjects[0].slug;
    const sessionSubject = isSubjectSlug(value.sessionSubject) ? value.sessionSubject : null;
    const endsAt = typeof value.endsAt === "number" && Number.isFinite(value.endsAt) ? value.endsAt : null;
    const remainingSeconds = typeof value.remainingSeconds === "number" && Number.isFinite(value.remainingSeconds)
      ? Math.max(0, Math.min(FOCUS_SECONDS, Math.floor(value.remainingSeconds)))
      : FOCUS_SECONDS;
    return {
      stats: {
        day: todayKey(),
        focusSessions: typeof rawStats.focusSessions === "number" ? Math.max(0, Math.floor(rawStats.focusSessions)) : 0,
        focusMinutes: typeof rawStats.focusMinutes === "number" ? Math.max(0, Math.floor(rawStats.focusMinutes)) : 0,
        bySubject,
      },
      phase,
      status,
      remainingSeconds,
      selectedSubject,
      sessionSubject,
      endsAt,
    };
  } catch {
    return null;
  }
}

export function StudyTimer() {
  const [phase, setPhase] = useState<Phase>("focus");
  const [status, setStatus] = useState<TimerStatus>("ready");
  const [remainingSeconds, setRemainingSeconds] = useState(FOCUS_SECONDS);
  const [selectedSubject, setSelectedSubject] = useState(studySubjects[0].slug);
  const [sessionSubject, setSessionSubject] = useState<string | null>(null);
  const [stats, setStats] = useState<DailyStats>(emptyStats);
  const [hydrated, setHydrated] = useState(false);
  const [notice, setNotice] = useState("25 dakika odaklan, sonra kısa bir mola ver.");

  const phaseRef = useRef(phase);
  const statusRef = useRef(status);
  const statsRef = useRef(stats);
  const selectedSubjectRef = useRef(selectedSubject);
  const sessionSubjectRef = useRef(sessionSubject);
  const endsAtRef = useRef<number | null>(null);
  phaseRef.current = phase;
  statusRef.current = status;
  statsRef.current = stats;
  selectedSubjectRef.current = selectedSubject;
  sessionSubjectRef.current = sessionSubject;

  const applyPhase = useCallback((nextPhase: Phase, nextStatus: TimerStatus, seconds: number) => {
    phaseRef.current = nextPhase;
    statusRef.current = nextStatus;
    endsAtRef.current = null;
    setPhase(nextPhase);
    setStatus(nextStatus);
    setRemainingSeconds(seconds);
  }, []);

  const completeCycleRef = useRef<(completedPhase: Phase) => void>(() => {});
  const completeCycle = useCallback((completedPhase: Phase) => {
    if (completedPhase === "focus") {
      const today = todayKey();
      const current = statsRef.current.day === today ? statsRef.current : emptyStats();
      const slug = sessionSubjectRef.current ?? selectedSubjectRef.current;
      const nextStats: DailyStats = {
        day: today,
        focusSessions: current.focusSessions + 1,
        focusMinutes: current.focusMinutes + 25,
        bySubject: { ...current.bySubject, [slug]: (current.bySubject[slug] ?? 0) + 25 },
      };
      statsRef.current = nextStats;
      setStats(nextStats);
      setSessionSubject(null);
      sessionSubjectRef.current = null;
      const nextBreak = nextStats.focusSessions % 4 === 0 ? "long-break" : "short-break";
      const breakSeconds = nextBreak === "long-break" ? LONG_BREAK_SECONDS : SHORT_BREAK_SECONDS;
      applyPhase(nextBreak, "ready", breakSeconds);
      setNotice(nextBreak === "long-break" ? "Dört odak oturumu tamamlandı. 15 dakikalık uzun mola hazır." : "Odak oturumu tamamlandı. Mola vermeye hazırsın.");
      return;
    }
    applyPhase("focus", "ready", FOCUS_SECONDS);
    setNotice("Mola bitti. Yeni bir odak oturumu başlatabilirsin.");
  }, [applyPhase]);
  completeCycleRef.current = completeCycle;

  useEffect(() => {
    const saved = readStoredState();
    if (!saved) {
      setHydrated(true);
      return;
    }
    let nextPhase = saved.phase;
    let nextStatus = saved.status;
    let nextSeconds = saved.remainingSeconds;
    let nextStats = saved.stats;
    let nextSessionSubject = saved.sessionSubject;
    let nextEndsAt = saved.endsAt;
    if (saved.status === "running") {
      const secondsLeft = nextEndsAt === null ? 0 : Math.ceil((nextEndsAt - Date.now()) / 1000);
      if (secondsLeft <= 0) {
        if (saved.phase === "focus") {
          const slug = saved.sessionSubject ?? saved.selectedSubject;
          nextStats = {
            ...saved.stats,
            focusSessions: saved.stats.focusSessions + 1,
            focusMinutes: saved.stats.focusMinutes + 25,
            bySubject: { ...saved.stats.bySubject, [slug]: (saved.stats.bySubject[slug] ?? 0) + 25 },
          };
          nextPhase = nextStats.focusSessions % 4 === 0 ? "long-break" : "short-break";
          nextSeconds = nextPhase === "long-break" ? LONG_BREAK_SECONDS : SHORT_BREAK_SECONDS;
          setNotice(nextPhase === "long-break" ? "Dört odak oturumu tamamlandı. 15 dakikalık uzun mola hazır." : "Odak oturumu tamamlandı. Mola vermeye hazırsın.");
          nextSessionSubject = null;
        } else {
          nextPhase = "focus";
          nextSeconds = FOCUS_SECONDS;
          setNotice("Mola bitti. Yeni bir odak oturumu başlatabilirsin.");
        }
        nextStatus = "ready";
        nextEndsAt = null;
      } else {
        nextSeconds = secondsLeft;
      }
    }
    setStats(nextStats);
    statsRef.current = nextStats;
    setPhase(nextPhase);
    phaseRef.current = nextPhase;
    setStatus(nextStatus);
    statusRef.current = nextStatus;
    setRemainingSeconds(nextSeconds);
    setSelectedSubject(saved.selectedSubject);
    selectedSubjectRef.current = saved.selectedSubject;
    setSessionSubject(nextSessionSubject);
    sessionSubjectRef.current = nextSessionSubject;
    endsAtRef.current = nextEndsAt;
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify({
        stats,
        phase,
        status,
        remainingSeconds,
        selectedSubject,
        sessionSubject,
        endsAt: endsAtRef.current,
      }));
    } catch {
      /* Depolama kapalıysa sayaç bu oturum boyunca çalışmaya devam eder. */
    }
  }, [hydrated, stats, phase, status, remainingSeconds, selectedSubject, sessionSubject]);

  useEffect(() => {
    if (status !== "running") return;
    const tick = () => {
      const endsAt = endsAtRef.current;
      if (endsAt === null) return;
      const secondsLeft = Math.max(0, Math.ceil((endsAt - Date.now()) / 1000));
      setRemainingSeconds(secondsLeft);
      if (secondsLeft === 0) {
        endsAtRef.current = null;
        completeCycleRef.current(phaseRef.current);
      }
    };
    const timer = window.setInterval(tick, 250);
    tick();
    return () => window.clearInterval(timer);
  }, [status, phase]);

  function startOrResume() {
    if (!hydrated || statusRef.current === "running") return;
    if (phaseRef.current === "focus" && sessionSubjectRef.current === null) {
      sessionSubjectRef.current = selectedSubjectRef.current;
      setSessionSubject(selectedSubjectRef.current);
    }
    endsAtRef.current = Date.now() + remainingSeconds * 1000;
    statusRef.current = "running";
    setStatus("running");
    setNotice(phaseRef.current === "focus" ? "Odak zamanı başladı. Bildirimleri sessize alıp tek derse odaklan." : "Mola zamanı başladı. Kısa bir ara ver.");
  }

  function pause() {
    if (statusRef.current !== "running") return;
    const endsAt = endsAtRef.current;
    const secondsLeft = endsAt === null ? remainingSeconds : Math.max(0, Math.ceil((endsAt - Date.now()) / 1000));
    endsAtRef.current = null;
    statusRef.current = "paused";
    setRemainingSeconds(secondsLeft);
    setStatus("paused");
    setNotice("Sayaç duraklatıldı; hazır olduğunda devam edebilirsin.");
  }

  function reset() {
    setSessionSubject(null);
    sessionSubjectRef.current = null;
    applyPhase("focus", "ready", FOCUS_SECONDS);
    setNotice("Sayaç sıfırlandı. Yeni bir odak oturumu başlatabilirsin.");
  }

  const phaseLabel = phase === "focus" ? "Odak zamanı" : phase === "long-break" ? "Uzun mola" : "Kısa mola";
  const actionLabel = status === "running" ? "Duraklat" : phase === "focus" ? (status === "paused" ? "Devam et" : "Başlat") : `${phaseLabel} başlat`;
  const subjectMinutes = Object.entries(stats.bySubject).sort((a, b) => b[1] - a[1]).slice(0, 3);

  return (
    <section className="card study-timer" aria-labelledby="study-timer-title">
      <div className="study-timer-heading">
        <span className="study-timer-icon" aria-hidden="true">⏱️</span>
        <div>
          <h2 id="study-timer-title">Çalışma Zamanlayıcısı</h2>
          <p>Pomodoro ile odak süreni takip et.</p>
        </div>
      </div>

      <div className={`study-timer-clock is-${phase}`}>
        <span>{phaseLabel}</span>
        <strong role="timer" aria-live="off">{formatClock(remainingSeconds)}</strong>
      </div>

      <label className="study-timer-subject">
        <span>Hangi derse çalışacaksın?</span>
        <select value={selectedSubject} onChange={(event) => setSelectedSubject(event.target.value)} disabled={!hydrated || status === "running" || sessionSubject !== null}>
          {studySubjects.map((subject) => <option value={subject.slug} key={subject.slug}>{subject.name}</option>)}
        </select>
      </label>

      <div className="study-timer-controls">
        <button type="button" className="btn btn-primary" onClick={status === "running" ? pause : startOrResume} disabled={!hydrated}>
          {actionLabel}
        </button>
        <button type="button" className="btn btn-ghost" onClick={reset} disabled={!hydrated}>Sıfırla</button>
      </div>

      <p className="study-timer-notice" aria-live="polite">{notice}</p>

      <div className="study-timer-stats" aria-label="Bugünkü çalışma özeti">
        <div><strong>{stats.focusSessions}</strong><span>odak oturumu</span></div>
        <div><strong>{stats.focusMinutes}</strong><span>dakika çalıştın</span></div>
      </div>

      {subjectMinutes.length > 0 && (
        <div className="study-timer-subjects">
          <small>Bugün derslere göre</small>
          <p>{subjectMinutes.map(([slug, minutes]) => `${studySubjects.find((subject) => subject.slug === slug)?.name}: ${minutes} dk`).join(" · ")}</p>
        </div>
      )}

      <p className="study-timer-cycle">25 dk odak · 5 dk kısa mola · 4 odak oturumundan sonra 15 dk uzun mola. Günlük özet yalnızca bu tarayıcıda saklanır.</p>
    </section>
  );
}
