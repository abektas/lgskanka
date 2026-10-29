"use client";

import { useEffect, useState } from "react";
import { computeUnitMasteries, formatDueLabel, subjectName, type UnitMastery } from "../lib/mastery";

/**
 * Ünite ustalığı + tekrar zamanı paneli (plan §14/§30/§45) — kural tabanlı.
 * Cevap kayıtlarından türetilir; Supabase gelene kadar tarayıcıda okunur.
 */
export function MasteryPanel() {
  const [items, setItems] = useState<UnitMastery[] | null>(null);

  useEffect(() => {
    setItems(computeUnitMasteries());
  }, []);

  if (items === null) return null;

  const dueCount = items.filter((m) => m.due).length;

  return (
    <section className="card" aria-labelledby="mastery-panel">
      <div className="section-head">
        <h2 id="mastery-panel">Ünite ustalığı ve tekrar zamanı</h2>
        <span className="pill">{dueCount > 0 ? `${dueCount} ünite tekrar bekliyor` : "Tekrar zamanı gelen yok"}</span>
      </div>
      {items.length === 0 ? (
        <p className="muted-text">
          Henüz cevap kaydı yok — soru çözdükçe ünite ustalığın burada birikir.
        </p>
      ) : (
        <div className="analysis-table">
          {items.map((m) => (
            <div className="analysis-row mastery-row" key={`${m.subject}-${m.unit ?? "x"}`}>
              <span>
                <b>{subjectName(m.subject)}</b>
                {m.unitName ? <small> · {m.unitName}</small> : null}
              </span>
              <span className="bar" aria-hidden="true">
                <i style={{ width: `${m.accuracy}%` }} />
              </span>
              <em>
                %{m.accuracy} · {m.level}
              </em>
              <small className={m.due ? "due" : ""}>tekrar: {formatDueLabel(m.nextReviewAt)}</small>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default MasteryPanel;