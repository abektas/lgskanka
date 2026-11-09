/**
 * Günlük 24 soruluk planı öğrencinin sonuçlarına göre oluşturur.
 *
 * Kural: her dersin kotası korunur (Türkçe/Mat/Fen 5, İnkılap/Din/İngilizce 3),
 * fakat o derste son günlerde yanlış yapılan ünitelerin soruları öne alınır.
 * Böylece bir günün sonucu ertesi günün soru seçimini belirler.
 */

export interface PlanQuestion {
  id: string;
  subject: string;
  unit: number | null;
  unitName: string | null;
}

export interface PlanWeakUnit {
  subject: string;
  unit: number | null;
  unitName: string | null;
}

function unitMatches(question: PlanQuestion, weak: PlanWeakUnit): boolean {
  if (question.subject !== weak.subject) return false;
  if (weak.unit !== null && question.unit !== null) return question.unit === weak.unit;
  if (weak.unitName && question.unitName) return question.unitName === weak.unitName;
  return false;
}

/**
 * Ders havuzlarını sırayla birleştirir; her derste önce zayıf ünite sorularını,
 * sonra kalan soruları alır. Kota dolunca ders atlanır, toplam kota korunur.
 */
export function composeDailyPlan<T extends PlanQuestion>(
  pools: Record<string, T[]>,
  limits: Record<string, number>,
  weakUnits: PlanWeakUnit[] = []
): T[] {
  const plan: T[] = [];
  const seen = new Set<string>();

  for (const [subject, limit] of Object.entries(limits)) {
    const pool = pools[subject] ?? [];
    if (limit <= 0 || pool.length === 0) continue;

    const subjectWeak = weakUnits.filter((w) => w.subject === subject);
    const priority: T[] = [];
    const rest: T[] = [];

    for (const question of pool) {
      if (seen.has(question.id)) continue;
      if (subjectWeak.some((w) => unitMatches(question, w))) priority.push(question);
      else rest.push(question);
    }

    for (const question of [...priority, ...rest]) {
      if (plan.filter((q) => q.subject === subject).length >= limit) break;
      if (seen.has(question.id)) continue;
      seen.add(question.id);
      plan.push(question);
    }
  }

  return plan;
}
