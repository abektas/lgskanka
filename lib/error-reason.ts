/**
 * Kural tabanlı hata nedeni sınıflandırma (Master Plan §6–§7) — AI'sız.
 *
 * Yanlış cevaptan sonra öğrenci kendi öz-değerlendirmesini seçer; seçenek
 * doğrudan H1–H7 koduna eşlenir. Sistem tahmin üretmez: öğrenci bir neden
 * seçmezse kayıt "sınıflandırılmadı" olarak kalır (NEEDS_REVIEW ruhu).
 */

export type ErrorReasonOption = {
  id: string;
  label: string;
  code: "H2" | "H3" | "H4" | "H7";
};

/** Plan §7: yanlış cevapta öğrenciye sunulan seçenekler. */
export const ERROR_REASON_OPTIONS: ErrorReasonOption[] = [
  { id: "anlamadim", label: "Soruyu anlamadım", code: "H3" },
  { id: "yonetim", label: "Yöntemi bilmiyordum", code: "H2" },
  { id: "islem", label: "İşlem hatası yaptım", code: "H4" },
  { id: "dikkat", label: "Dikkatim dağıldı", code: "H7" },
];

/** Plan §41: cevap kaydı. Supabase gelene kadar tarayıcıda saklanır. */
export type AnswerRecord = {
  questionId: string;
  subject: string;
  /** Konu/ünite takibi (plan §30) — mastery bunlardan türetilir. */
  unit: number | null;
  unitName: string | null;
  topic: string | null;
  selectedAnswer: string;
  correct: boolean;
  /** Öğrencinin seçtiği hata nedeninin H kodu; seçilmediyse null. */
  errorReasonCode: string | null;
  timeSpentSec: number;
  createdAt: string;
};

const STORAGE_KEY = "lgs_answer_log";
const MAX_RECORDS = 500;

export function saveAnswerRecord(record: AnswerRecord): void {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const list: AnswerRecord[] = raw ? JSON.parse(raw) : [];
    list.push(record);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list.slice(-MAX_RECORDS)));
  } catch {
    // Depolama kapalıysa kayıt sessizce atlanır.
  }
}

export function loadAnswerRecords(): AnswerRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const list = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}