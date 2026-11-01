"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "./icons";
import { apiFetch } from "../lib/sync";

interface ContinueData {
  today: { solved: number; correct: number; target: number };
  exam: { month: number; answers: Record<string, string> } | null;
  suggestion: { title: string; detail: string; href: string };
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
  const pct = Math.min(100, Math.round((today.solved / Math.max(1, today.target)) * 100));

  return (
    <section className="card continue-card" aria-labelledby="kaldigin-yerden">
      <div className="continue-icon" aria-hidden="true">
        🚀
      </div>
      <div className="continue-body">
        <span className="eyebrow">Kaldığın yerden devam et</span>
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
        <small className="muted-text">
          Bugün {today.solved}/{today.target} soru · {today.correct} doğru
        </small>

        <Link className="btn btn-primary" href={suggestion.href}>
          Devam et <Icon name="arrow" size={18} />
        </Link>
      </div>
    </section>
  );
}