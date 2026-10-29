"use client";

import { useEffect, useState } from "react";
import {
  computeCycleState,
  cycleSummary,
  ENROLLMENT_CHANGED_EVENT,
  type CycleState,
} from "../lib/cycle";

/** Sınav sayfalarında döngü bağlamını gösteren küçük rozet. */
export function CycleBadge({ variant }: { variant?: "haftalik" | "aylik" }) {
  const [cycle, setCycle] = useState<CycleState | null>(null);

  useEffect(() => {
    setCycle(computeCycleState());
    const onChange = () => setCycle(computeCycleState());
    window.addEventListener(ENROLLMENT_CHANGED_EVENT, onChange);
    return () => window.removeEventListener(ENROLLMENT_CHANGED_EVENT, onChange);
  }, []);

  if (!cycle) return null;

  const isExpected = variant ? cycle.weekendTest === variant : true;

  return (
    <div className="cycle-badge" role="status">
      <span className="pill is-mint">
        {cycle.cycleNumber}. döngü · {cycle.cycleWeek}. hafta
      </span>
      <p className="muted-text">{cycleSummary(cycle, variant)}</p>
    </div>
  );
}
