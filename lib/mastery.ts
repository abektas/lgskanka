/**
 * Kural tabanlı mastery + tekrar zamanlaması (Master Plan §14, §30, §45) — AI'sız.
 *
 * Tümü cevap kayıtlarından (doğru/yanlış + konu/ünite) türetilir; ayrı durum
 * saklanmaz, aynı kayıt geçmişi aynı sonucu verir (saf fonksiyonlar).
 */
import { loadAnswerRecords, type AnswerRecord } from "./error-reason";

/** Plan §14: tekrar aralıkları (gün). Yanlışta başa döner. */
const INTERVALS_DAYS = [1, 3, 7, 14, 30];

/** Plan §45: mastery bantları. */
export type MasteryLevel = "zayıf" | "gelişiyor" | "yeterli" | "güçlü";

export type UnitMastery = {
  subject: string;
  unit: number | null;
  unitName: string | null;
  total: number;
  correct: number;
  /** 0–100 */
  accuracy: number;
  level: MasteryLevel;
  /** ISO tarih — sonraki tekrar zamanı */
  nextReviewAt: string;
  /** Tekrar zamanı geldi mi (şimdi veya geçmiş) */
  due: boolean;
};

export function masteryLevel(accuracy: number): MasteryLevel {
  if (accuracy < 40) return "zayıf";
  if (accuracy < 60) return "gelişiyor";
  if (accuracy < 80) return "yeterli";
  return "güçlü";
}

/**
 * Tekrar zamanı türetimi: her doğru cevap aralığı bir kademe ilerletir
 * (1→3→7→14→30 gün), yanlış cevap aralığı başa döner (1 gün).
 */
function nextReviewFrom(records: AnswerRecord[]): Date {
  const sorted = [...records].sort((a, b) => a.createdAt.localeCompare(b.createdAt));
  let stage = 0;
  for (const r of sorted) {
    stage = r.correct ? Math.min(stage + 1, INTERVALS_DAYS.length - 1) : 0;
  }
  const last = new Date(sorted[sorted.length - 1].createdAt);
  const next = new Date(last.getTime() + INTERVALS_DAYS[stage] * 24 * 60 * 60 * 1000);
  return next;
}

export function computeUnitMasteries(
  records: AnswerRecord[] = loadAnswerRecords(),
  now: Date = new Date()
): UnitMastery[] {
  const groups = new Map<string, AnswerRecord[]>();
  for (const r of records) {
    const key = `${r.subject}|${r.unit ?? "-"}`;
    const list = groups.get(key) ?? [];
    list.push(r);
    groups.set(key, list);
  }
  const result: UnitMastery[] = [];
  for (const list of groups.values()) {
    const total = list.length;
    const correct = list.filter((r) => r.correct).length;
    const accuracy = Math.round((correct / total) * 100);
    const nextReview = nextReviewFrom(list);
    const sample = list[list.length - 1];
    result.push({
      subject: sample.subject,
      unit: sample.unit,
      unitName: sample.unitName,
      total,
      correct,
      accuracy,
      level: masteryLevel(accuracy),
      nextReviewAt: nextReview.toISOString(),
      due: nextReview.getTime() <= now.getTime(),
    });
  }
  // Zayıf ve tekrar zamanı gelen üniteler üstte
  return result.sort((a, b) => {
    if (a.due !== b.due) return a.due ? -1 : 1;
    return a.accuracy - b.accuracy;
  });
}

/** "bugün" / "yarın" / "3 gün sonra" / "12 gün önce gecikti" */
export function formatDueLabel(iso: string, now: Date = new Date()): string {
  const target = new Date(iso);
  const days = Math.round((target.getTime() - now.getTime()) / (24 * 60 * 60 * 1000));
  if (days <= -2) return `${-days} gün önce gecikti`;
  if (days === -1) return "dünden gecikti";
  if (days === 0) return "bugün";
  if (days === 1) return "yarın";
  return `${days} gün sonra`;
}

/** Ders adları arayüzde tek yerden gelsin. */
export const SUBJECT_NAMES: Record<string, string> = {
  turkce: "Türkçe",
  matematik: "Matematik",
  fen: "Fen Bilimleri",
  "fen-bilimleri": "Fen Bilimleri",
  ingilizce: "İngilizce",
  din: "Din Kültürü",
  "din-kulturu": "Din Kültürü",
  inkilap: "İnkılap Tarihi",
  "inkilap-tarihi": "İnkılap Tarihi",
};

export function subjectName(slug: string): string {
  return SUBJECT_NAMES[slug] ?? slug;
}