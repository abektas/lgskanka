import { NextRequest, NextResponse } from "next/server";
import { dbSelect } from "../../../lib/db";
import { authFromRequest } from "../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * GET /api/exams-status
 * Girişli öğrencinin tamamladığı aylık denemeleri döndürür.
 *
 * localStorage kaybına karşı sunucu tarafı doğrulama sağlar:
 * /aylik-denemeler sayfası bu listeyi yerel kayıtla birleştirir.
 */
export async function GET(request: NextRequest) {
  try {
    const auth = await authFromRequest(request);
    if (!auth) {
      return NextResponse.json({ completedMonths: [], results: [] });
    }

    const rows = await dbSelect<{
      month: number;
      month_name: string;
      correct: number;
      wrong: number;
      empty: number;
      percentage: number;
      level: string;
      by_subject: Record<string, { correct: number; wrong: number; empty: number; total: number }>;
      completed_at: string;
    }>(
      "exam_results",
      `student_id=eq.${encodeURIComponent(auth.sub)}&order=completed_at.desc`,
      "month,month_name,correct,wrong,empty,percentage,level,by_subject,completed_at"
    );

    // Aynı ay birden çok kez çözülmüşse en yenisi geçerli
    const seen = new Set<number>();
    const results: Array<Record<string, unknown>> = [];
    const completedMonths: number[] = [];
    for (const r of rows) {
      if (seen.has(r.month)) continue;
      seen.add(r.month);
      completedMonths.push(r.month);
      results.push({
        month: r.month,
        monthName: r.month_name,
        total: r.correct + r.wrong + r.empty,
        correct: r.correct,
        wrong: r.wrong,
        empty: r.empty,
        percentage: r.percentage,
        level: r.level,
        bySubject: r.by_subject,
        completedAt: r.completed_at,
      });
    }

    return NextResponse.json({ completedMonths, results });
  } catch (e) {
    return NextResponse.json(
      { completedMonths: [], results: [], error: String(e).slice(0, 200) },
      { status: 500 }
    );
  }
}
