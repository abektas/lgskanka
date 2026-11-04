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
  /** Source assessment, kept distinct when the same question appears again. */
  source?: string;
  createdAt: string;
};

const STORAGE_KEY = "lgs_answer_log";
const MAX_RECORDS = 500;

/**
 * Cevap kaydı: önce sunucuya gönderilir (gerçek veri), sonra yerel
 * aynaya yazılır (hızlı görüntüleme için).
 */
export function saveAnswerRecord(record: AnswerRecord): void {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const list: AnswerRecord[] = raw ? JSON.parse(raw) : [];
    list.push(record);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list.slice(-MAX_RECORDS)));
    window.dispatchEvent(new Event("lgs-answer-records-changed"));
  } catch {
    // Depolama kapalıysa kayıt sessizce atlanır.
  }
  // Online senkron (ateşle-unut)
  import("./sync").then(({ pushAnswerRecord }) => pushAnswerRecord(record));
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

/** Sunucudan gelen kayıtlarla yerel aynayı birleştir. */
export function hydrateAnswerLog(records: AnswerRecord[]): void {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const local: AnswerRecord[] = raw ? JSON.parse(raw) : [];
    // Kaynak başına tek kayıt — sunucudaki upsert (student_id,question_id,source) ile aynı.
    const byQuestion = new Map<string, AnswerRecord>();
    const recordKey = (r: AnswerRecord) => `${r.questionId}:${r.source ?? "gunluk"}`;
    const put = (r: AnswerRecord) => {
      if (!r || !r.questionId) return;
      const key = recordKey(r);
      const prev = byQuestion.get(key);
      if (!prev || String(r.createdAt) >= String(prev.createdAt)) byQuestion.set(key, r);
    };
    if (Array.isArray(local)) local.forEach(put);
    records.forEach(put);

    const serverKeys = new Set(records.map(recordKey));
    const missing = [...byQuestion.values()].filter((r) => !serverKeys.has(recordKey(r)));

    const merged = [...byQuestion.values()].sort((a, b) =>
      String(a.createdAt).localeCompare(String(b.createdAt))
    );
    localStorage.setItem(STORAGE_KEY, JSON.stringify(merged.slice(-MAX_RECORDS)));
    window.dispatchEvent(new Event("lgs-answer-records-changed"));

    // Sunucuya hiç ulaşmamış yerel kayıtları yeniden gönder (kendini onaran ayna).
    if (missing.length > 0) {
      import("./sync").then(({ pushAnswerRecord }) => {
        for (const r of missing) pushAnswerRecord(r);
      });
    }
  } catch {
    /* yok say */
  }
}