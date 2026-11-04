"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "./icons";
import { ScoreCounts } from "./score-counts";
import { apiFetch } from "../lib/sync";

interface ContinueData {
  today: { solved: number; correct: number; target: number; completed?: boolean };
  exam: { month: number; answers: Record<string, string> } | null;
  suggestion: { title: string; detail: string; href: string };
  done?: boolean;
}

/**
 * Ana sayfa kartı: "Kaldığın yerden devam et".
 *
 * Sunucudan günlük çalışma durumu ve yarım kalmış deneme bilgisini
 * çeker; öğrenci her cihazda kaldığı yerden devam eder.
 */
export function ContinueCard() {
  const [data, setData] = useState<ContinueData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    apiFetch("/api/continue")
      .then((res) => (res.ok ? res.json() : null))
      .then((d) => {
        if (!cancelled && d) setData(d);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading || !data) return null;

  const { today, suggestion } = data;
  const done = data.done === true;
  const total = Math.max(0, today.target);
  const answered = Math.min(total, Math.max(0, today.solved));
  const correct = Math.min(answered, Math.max(0, today.correct));
  const pct = done ? 100 : Math.min(100, Math.round((today.solved / Math.max(1, today.target)) * 100));

  return (
    <section className="card continue-card" aria-labelledby="kaldigin-yerden">
      <div className="continue-icon" aria-hidden="true">
        {done ? "🎉" : "🚀"}
      </div>
      <div className="continue-body">
        <span className="eyebrow">
          {done ? "Günlük çalışma tamamlandı" : "Kaldığın yerden devam et"}
        </span>
        <h2 id="kaldigin-yerden">{suggestion.title}</h2>
        <p className="continue-detail">{suggestion.detail}</p>

        <div
          className="bar"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={today.target}
          aria-valuenow={today.solved}
          aria-label="Bugünkü ilerlemen"
        >
          <i style={{ width: `${pct}%` }} />
        </div>
        <div className="muted-text">
          <small>Bugün</small>
          <ScoreCounts correct={correct} wrong={answered - correct} blank={total - answered} total={total} />
        </div>

        {!done && (
          <Link className="btn btn-primary" href={suggestion.href}>
            Devam et <Icon name="arrow" size={18} />
          </Link>
        )}
      </div>
    </section>
  );
}