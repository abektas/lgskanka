/**
 * LGS resmi puanlama sistemi yardımcıları.
 * 2018+ LGS için ham puan: Doğru - (Yanlış / 4)
 * Yerleştirme puanı daha karmaşıktır (ders katsayıları, standart sapma vb.),
 * burada "yaklaşık ham puan" hesaplanır.
 */

export interface ExamScoreInput {
  correct: number;
  wrong: number;
  empty: number;
  total: number;
}

export interface ExamScoreResult {
  rawScore: number;           // Ham puan: Doğru - Yanlış/4
  percentage: number;         // Yüzde başarı
  correct: number;
  wrong: number;
  empty: number;
  total: number;
}

/** LGS ham puanını hesaplar: Doğru - (Yanlış / 4) */
export function calculateRawScore(input: ExamScoreInput): ExamScoreResult {
  const { correct, wrong, empty, total } = input;
  const rawScore = correct - wrong / 4;
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