/**
 * Sonuçlar ve İlerleme — gerçek veri analitiği (AI'sız, kural tabanlı).
 *
 * Tüm metrikler cevap kayıtlarından (lgs_answer_log) ve değerlendirme
 * geçmişlerinden (haftalık test + aylık deneme) türetilir. Demo sabit veri
 * kullanılmaz; kayıt yoksa sayfa boş durumu gösterir.
 */

import { loadAnswerRecords, type AnswerRecord } from "./error-reason";
import { computeUnitMasteries, subjectName, type UnitMastery } from "./mastery";
import { loadWeeklyTestHistory, type WeeklyTestRecord } from "./weekly-test-history";
import { loadExamHistory, type ExamRecord } from "./exam-history";

/** H kodu → görünen ad. */
export const H_LABELS: Record<string, string> = {
  H1: "Kavramsal eksiklik",
  H2: "Yöntem / strateji hatası",
  H3: "Soruyu anlamama",
  H4: "İşlem hatası",
  H5: "Gereksiz bilgi",
  H6: "Bilgileri ilişkilendirme",
  H7: "Dikkat / acele",
};

/** Genel özet metrikleri. */
export interface OverallStats {
  totalAnswered: number;
  totalCorrect: number;
  totalWrong: number;
  /** 0–100 */
  accuracy: number;
  /** Son 7 günde çözülen soru */
  thisWeek: number;
  /** H türü seçilmiş yanlış sayısı */
  classified: number;
  /** Toplam yanlış */
  wrong: number;
}

/** Cevap kayıtlarından genel özet. */
export function computeOverallStats(records: AnswerRecord[] = loadAnswerRecords()): OverallStats {
  const totalAnswered = records.length;
  const totalCorrect = records.filter((r) => r.correct).length;
  const totalWrong = totalAnswered - totalCorrect;
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const thisWeek = records.filter((r) => new Date(r.createdAt).getTime() >= weekAgo).length;
  const classified = records.filter((r) => !r.correct && r.errorReasonCode).length;
  return {
    totalAnswered,
    totalCorrect,
    totalWrong,
    accuracy: totalAnswered > 0 ? Math.round((totalCorrect / totalAnswered) * 100) : 0,
    thisWeek,
    classified,
    wrong: totalWrong,
  };
}

/** H türü dağılımı — gerçek yanlış kayıtlarından. */
export function computeErrorBreakdown(
  records: AnswerRecord[] = loadAnswerRecords()
): Array<{ code: string; label: string; count: number; share: number }> {
  const counts = new Map<string, number>();
  for (const r of records) {
    if (r.correct) continue;
    const code = r.errorReasonCode;
    if (!code || code === "SKIPPED") continue;
    counts.set(code, (counts.get(code) ?? 0) + 1);
  }
  const total = [...counts.values()].reduce((a, b) => a + b, 0);
  const allCodes = ["H1", "H2", "H3", "H4", "H5", "H6", "H7"];
  return allCodes.map((code) => {
    const count = counts.get(code) ?? 0;
    return {
      code,
      label: H_LABELS[code] ?? code,
      count,
      share: total > 0 ? Math.round((count / total) * 100) : 0,
    };
  });
}

/** Ders bazlı doğruluk. */
export function computeSubjectAccuracy(
  records: AnswerRecord[] = loadAnswerRecords()
): Array<{ subject: string; name: string; total: number; correct: number; accuracy: number }> {
  const map = new Map<string, { total: number; correct: number }>();
  for (const r of records) {
    const cur = map.get(r.subject) ?? { total: 0, correct: 0 };
    cur.total++;
    if (r.correct) cur.correct++;
    map.set(r.subject, cur);
  }
  return [...map.entries()]
    .map(([subject, v]) => ({
      subject,
      name: subjectName(subject),
      total: v.total,
      correct: v.correct,
      accuracy: v.total > 0 ? Math.round((v.correct / v.total) * 100) : 0,
    }))
    .sort((a, b) => a.accuracy - b.accuracy);
}

/** Zayıf konu/ünite listesi — 2+ yanlış olan gruplar. */
export interface WeakTopic {
  key: string;
  subject: string;
  name: string;
  unit: number | null;
  unitName: string | null;
  topic: string | null;
  wrongCount: number;
  total: number;
  accuracy: number;
  sources: string[];
}

/**
 * Zayıf konuları üç kaynaktan birleştirir:
 * - günlük/haftalık cevap kayıtları (lgs_answer_log)
 * - aylık deneme kayıtları (lgs_exam_history)
 * - haftalık test kayıtları (lgs_weekly_test_history)
 */
export function computeWeakTopics(
  records: AnswerRecord[] = loadAnswerRecords(),
  exams: ExamRecord[] = loadExamHistory(),
  weekly: WeeklyTestRecord[] = loadWeeklyTestHistory()
): WeakTopic[] {
  const map = new Map<string, WeakTopic>();
  const touch = (
    subject: string,
    unit: number | null,
    unitName: string | null,
    topic: string | null,
    wrong: number,
    total: number,
    source: string
  ) => {
    const key = `${subject}|${unit ?? "-"}|${topic ?? "-"}`;
    const existing = map.get(key) ?? {
      key,
      subject,
      name: subjectName(subject),
      unit,
      unitName,
      topic,
      wrongCount: 0,
      total: 0,
      accuracy: 0,
      sources: [],
    };
    existing.wrongCount += wrong;
    existing.total += total;
    if (!existing.sources.includes(source)) existing.sources.push(source);
    map.set(key, existing);
  };

  // 1) Cevap kayıtları (günlük + haftalık testler)
  const byKey = new Map<string, { wrong: number; total: number }>();
  for (const r of records) {
    const key = `${r.subject}|${r.unit ?? "-"}|${r.topic ?? "-"}`;
    const cur = byKey.get(key) ?? { wrong: 0, total: 0 };
    cur.total++;
    if (!r.correct) cur.wrong++;
    byKey.set(key, cur);
  }
  for (const r of records) {
    const key = `${r.subject}|${r.unit ?? "-"}|${r.topic ?? "-"}`;
    const cur = byKey.get(key);
    if (!cur) continue;
    touch(r.subject, r.unit, r.unitName, r.topic, 0, 0, "günlük");
    const entry = map.get(key);
    if (entry) entry.total = cur.total;
  }

  // 2) Aylık denemeler
  for (const ex of exams) {
    const grouped = new Map<string, { wrong: number; total: number; unit: number | null; unitName: string | null; topic: string | null }>();
    for (const d of ex.details) {
      const key = `${d.subject}|${d.unit ?? "-"}|${d.topic ?? "-"}`;
      const cur = grouped.get(key) ?? { wrong: 0, total: 0, unit: d.unit, unitName: null, topic: d.topic };
      cur.total++;
      if (!d.isCorrect) cur.wrong++;
      grouped.set(key, cur);
    }
    for (const [key, v] of grouped) {
      touch(
        key.split("|")[0],
        v.unit,
        v.unitName,
        v.topic,
        v.wrong,
        v.total,
        "aylık deneme"
      );
    }
  }

  // 3) Haftalık testler — yalnızca zayıf ünite listesi üzerinden
  for (const w of weekly) {
    for (const u of w.weakUnits) {
      touch(u.subject, u.unit, u.unitName, null, 0, 0, "haftalık test");
    }
  }

  const result = [...map.values()];
  for (const t of result) {
    t.accuracy = t.total > 0 ? Math.round(((t.total - t.wrongCount) / t.total) * 100) : 0;
  }
  // En çok yanlış → en az yanlış
  return result
    .filter((t) => t.wrongCount >= 2 || t.accuracy < 60)
    .sort((a, b) => b.wrongCount - a.wrongCount || a.accuracy - b.accuracy);
}

/** Değerlendirme geçmişi — birleşik (aylık + haftalık). */
export interface UnifiedResult {
  id: string;
  date: string;
  kind: "aylik" | "haftalik";
  title: string;
  total: number;
  correct: number;
  wrong: number;
  empty: number;
  percentage: number;
}

/** Aylık deneme + haftalık test geçmişini tek listede birleştirir. */
export function computeUnifiedResults(
  exams: ExamRecord[] = loadExamHistory(),
  weekly: WeeklyTestRecord[] = loadWeeklyTestHistory()
): UnifiedResult[] {
  const fromExams: UnifiedResult[] = exams.map((e) => ({
    id: `exam-${e.month}-${e.date}`,
    date: e.date,
    kind: "aylik",
    title: e.month === 0 ? "Seviye Tespit" : `${e.month}. Ay Denemesi`,
    total: e.total,
    correct: e.correct,
    wrong: e.wrong,
    empty: e.empty,
    percentage: e.percentage,
  }));
  const fromWeekly: UnifiedResult[] = weekly.map((w) => ({
    id: `weekly-${w.date}`,
    date: w.date,
    kind: "haftalik",
    title: "Haftalık Test",
    total: w.total,
    correct: w.correct,
    wrong: w.wrong,
    empty: w.blank,
    percentage: w.total > 0 ? Math.round((w.correct / w.total) * 100) : 0,
  }));
  return [...fromExams, ...fromWeekly].sort((a, b) => b.date.localeCompare(a.date));
}

/** Mastery bantları — gerçek ünite ustalığından. */
export function computeMasteryBands(
  masteries: UnitMastery[] = computeUnitMasteries()
): Array<{ level: string; label: string; count: number; tone: string; advice: string }> {
  const bands = [
    { level: "zayıf", label: "Zayıf", tone: "kirmizi", advice: "Öncelikle pekiştirme" },
    { level: "gelişiyor", label: "Gelişiyor", tone: "seftali", advice: "Tekrar çalış" },
    { level: "yeterli", label: "Yeterli", tone: "limon", advice: "Aralıklı tekrar" },
    { level: "güçlü", label: "Güçlü", tone: "mint", advice: "Sadece bakım" },
  ];
  return bands.map((b) => ({
    ...b,
    count: masteries.filter((m) => m.level === b.level).length,
  }));
}
