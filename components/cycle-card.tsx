"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "./icons";
import {
  computeCycleState,
  cycleSummary,
  dayTypeLabel,
  ENROLLMENT_CHANGED_EVENT,
  type CycleState,
} from "../lib/cycle";

/**
 * Çalışma döngüsü kartı — kayıt tarihinden başlayan 4 haftalık ritim.
 * 1-3. hafta haftalık test, 4. hafta aylık deneme.
 * Hafta sonu (cumartesi ve pazar) esnek: ikisinden birine girilebilir.
 */
export function CycleCard() {
  const [cycle, setCycle] = useState<CycleState | null>(null);

  useEffect(() => {
    setCycle(computeCycleState());
    const onChange = () => setCycle(computeCycleState());
    window.addEventListener(ENROLLMENT_CHANGED_EVENT, onChange);
    return () => window.removeEventListener(ENROLLMENT_CHANGED_EVENT, onChange);
  }, []);

  if (!cycle) {
    return (
      <section className="card" aria-labelledby="dongu">
        <div className="section-head">
          <h2 id="dongu">Çalışma Döngüsü</h2>
        </div>
        <p className="muted-text">Döngü hesaplanıyor…</p>
      </section>
    );
  }

  const testHref = cycle.weekendTest === "aylik" ? "/aylik-denemeler" : "/haftalik-test";
  const testLabel = cycle.weekendTest === "aylik" ? "Aylık Deneme" : "Haftalık Test";

  const steps = [
    { week: 1, label: "Haftalık Test", done: cycle.cycleWeek > 1 },
    { week: 2, label: "Haftalık Test", done: cycle.cycleWeek > 2 },
    { week: 3, label: "Haftalık Test", done: cycle.cycleWeek > 3 },
    { week: 4, label: "Aylık Deneme", done: false },
  ];

  return (
    <section className="card" aria-labelledby="dongu">
      <div className="section-head">
        <h2 id="dongu">Çalışma Döngüsü</h2>
        <span className="pill is-mint">
          {cycle.cycleNumber}. döngü · {cycle.cycleWeek}. hafta
        </span>
      </div>

      <p className="coach-note">{cycleSummary(cycle)}</p>

      <ol className="cycle-steps" aria-label="Döngü haftaları">
        {steps.map((step) => {
          const active = cycle.cycleWeek === step.week;
          const state = step.done ? "done" : active ? "active" : "upcoming";
          return (
            <li className={`cycle-step is-${state}`} key={step.week}>
              <span className="cycle-step-week">{step.week}. hafta</span>
              <span className="cycle-step-label">{step.label}</span>
              {step.done && <span className="cycle-step-mark">✓</span>}
              {active && <span className="cycle-step-mark">●</span>}
            </li>
          );
        })}
      </ol>

      <div className="cycle-today">
        <div>
          <span className="eyebrow">Bugün</span>
          <b>{dayTypeLabel(cycle.dayType)}</b>
          {cycle.isWeekend && (
            <small className="muted-text">
              Cumartesi ve pazar aynı teste girebilirsin — hangi gün uygunsa o gün çöz.
            </small>
          )}
        </div>
        {cycle.isWeekend ? (
          <Link className="btn btn-primary" href={testHref}>
            {testLabel} <Icon name="arrow" size={18} />
          </Link>
        ) : (
          <Link className="btn btn-soft" href="/calis">
            Günlük Alıştırma <Icon name="arrow" size={18} />
          </Link>
        )}
      </div>

      <p className="muted-text" style={{ marginTop: 12, fontSize: 12.5 }}>
        Kayıt tarihinden itibaren {cycle.daysSinceEnrollment} gün geçti. Döngü her 4 haftada bir
        tekrarlanır.
      </p>
    </section>
  );
}
