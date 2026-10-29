/**
 * Aylık deneme sonuçları — kalıcı kayıt (localStorage).
 *
 * Her deneme bitişinde özet + ders bazlı döküm + zayıf üniteler kaydedilir.
 * "Sonuçlar ve İlerleme" sayfası bu kayıtları okur.
 */

export const EXAM_HISTORY_KEY = "lgs_exam_history";

/** Bir aylık deneme kaydı. */
export interface ExamRecord {
  /** ISO tarih (denemenin bittiği an) */
  date: string;
  /** Deneme dönemi (0 = seviye tespit, 1-11 = aylar) */
  month: number;
  /** Dönem adı (00_seviye_tespit, 01_ay, ...) */
  monthName: string;
  total: number;
  correct: number;
  wrong: number;
  empty: number;
  percentage: number;
  level: string;
  /** Ders bazlı döküm */
  bySubject: Record<string, { correct: number; wrong: number; empty: number; total: number }>;
  /** Soru bazlı detay (zayıf konu analizi için) */
  details: Array<{
    questionId: string;
    subject: string;
    given: string | null;
    correct: string | null;
    isCorrect: boolean;
    topic: string | null;
    unit: number | null;
    difficultyScore: number;
  }>;
}

/** Geçmiş kayıtlarını okur (en yenisi sonda). */
export function loadExamHistory(): ExamRecord[] {
  try {
    const raw = localStorage.getItem(EXAM_HISTORY_KEY);
    const list = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

/** Yeni bir deneme kaydını sona ekler (en fazla 24 kayıt tutulur). */
export function saveExamRecord(record: ExamRecord): ExamRecord[] {
  const history = loadExamHistory();
  history.push(record);
  const trimmed = history.slice(-24);
  try {
    localStorage.setItem(EXAM_HISTORY_KEY, JSON.stringify(trimmed));
  } catch {
    // Depolama hatası sessizce atlanır
  }
  return trimmed;
}

/** Son kaydı döndürür (yoksa null). */
export function latestExam(): ExamRecord | null {
  const history = loadExamHistory();
  return history.length > 0 ? history[history.length - 1] : null;
}

/** Son N kaydı döndürür (en yenisi önce). */
export function recentExams(n: number = 5): ExamRecord[] {
  return loadExamHistory().slice(-n).reverse();
}

/** Bir önceki denemeye göre değişim (+/- puan). */
export function examDelta(): number {
  const recent = recentExams(2);
  if (recent.length < 2) return 0;
  return Math.round(recent[0].percentage - recent[1].percentage);
}

/**
 * Deneme sonuçlarından konu/ünite bazlı yanlış dağılımı çıkarır.
 * topic null ise ünite bazında, o da yoksa ders bazında gruplar.
 */
export function weakTopicsFromExams(records: ExamRecord[]): Array<{
  subject: string;
  unit: number | null;
  topic: string | null;
  wrongCount: number;
  source: "aylik";
}> {
  const map = new Map<string, { subject: string; unit: number | null; topic: string | null; wrongCount: number }>();
  for (const rec of records) {
    for (const d of rec.details) {
      if (d.isCorrect) continue;
      const key = `${d.subject}|${d.unit ?? "-"}|${d.topic ?? "-"}`;
      const existing = map.get(key) ?? {
        subject: d.subject,
        unit: d.unit,
        topic: d.topic,
        wrongCount: 0,
      };
      existing.wrongCount++;
      map.set(key, existing);
    }
  }
  return [...map.values()].map((v) => ({ ...v, source: "aylik" as const }));
}