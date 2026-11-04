type ScoreCountsProps = {
  correct: number;
  wrong: number;
  blank: number | null;
  total: number;
};

export function ScoreCounts({ correct, wrong, blank, total }: ScoreCountsProps) {
  return (
    <span className="score-counts">
      <span>Doğru: {correct}</span>
      <span>Yanlış: {wrong}</span>
      <span>Boş: {blank ?? "—"}</span>
      <span>Toplam: {total}</span>
    </span>
  );
}
