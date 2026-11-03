/**
 * LGS resmi puanlama sistemi yardımcıları.
 * MEB LGS kılavuzu ("Sınavın Değerlendirilmesi"): ham puan = Doğru − (Yanlış / 3)
 * — "3 yanlış 1 doğruyu götürür". (÷4 kuralı ÖSYM/YKS içindir, LGS değil.)
 * Yerleştirme puanı (MSP) daha karmaşıktır: test başına ortalama/standart sapma ile
 * standart puan (ort 50, ss 10), MEB katsayıları ve TASP gerekir — burada yalnızca
 * resmî ham puan (net) hesaplanır.
 */

export interface ExamScoreInput {
  correct: number;
  wrong: number;
  empty: number;
  total: number;
}

export interface ExamScoreResult {
  rawScore: number;           // Ham puan (net): Doğru - Yanlış/3
  percentage: number;         // Yüzde başarı
  correct: number;
  wrong: number;
  empty: number;
  total: number;
}

/** LGS ham puanını hesaplar: Doğru - (Yanlış / 3) — MEB kılavuzu, 3 yanlış 1 doğruyu götürür */
export function calculateRawScore(input: ExamScoreInput): ExamScoreResult {
  const { correct, wrong, empty, total } = input;
  const rawScore = correct - wrong / 3;
  const percentage = total > 0 ? Math.round((correct / total) * 100) : 0;
  return {
    rawScore: Math.max(0, Math.round(rawScore * 100) / 100), // 2 ondalık
    percentage,
    correct,
    wrong,
    empty,
    total,
  };
}

/** Deneme sonucundan LGS ham puanını hesaplar (by_subject dâhil) */
export function calculateExamScore(result: {
  correct: number;
  wrong: number;
  empty: number;
  total: number;
  by_subject?: Record<string, { correct: number; wrong: number; empty: number; total: number }>;
}) {
  const overall = calculateRawScore({
    correct: result.correct,
    wrong: result.wrong,
    empty: result.empty,
    total: result.total,
  });

  let bySubject: Record<string, ExamScoreResult> | undefined;
  if (result.by_subject) {
    bySubject = {};
    for (const [subject, stats] of Object.entries(result.by_subject)) {
      bySubject[subject] = calculateRawScore({
        correct: stats.correct,
        wrong: stats.wrong,
        empty: stats.empty,
        total: stats.total,
      });
    }
  }

  return {
    overall,
    bySubject,
  };
}