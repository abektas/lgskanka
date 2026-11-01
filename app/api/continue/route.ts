import { NextRequest, NextResponse } from "next/server";
import { dbSelectOne, dbSelect } from "../../../lib/db";
import { authFromRequest } from "../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

/**
 * "Kaldığın yerden devam et" verisi.
 *
 * Döner:
 * - today: bugünkü günlük çalışma durumu (kaç soru çözüldü, hedef)
 * - exam: yarım kalmış deneme (varsa)
 * - suggestion: kartta gösterilecek öneri metni + hedef URL
 */
export async function GET(request: NextRequest) {
  const auth = await authFromRequest(request);
  if (!auth) return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });

  try {
    const date = today();

    // 1) Bugünkü günlük çalışma
    const study = await dbSelectOne<{
      solved: number;
      correct: number;
      target: number;
      state: Record<string, unknown>;
    }>(
      "study_sessions",
      `student_id=eq.${encodeURIComponent(auth.sub)}&session_date=eq.${date}`
    );

    // 2) Yarım kalmış deneme (en son güncellenen)
    const examRows = await dbSelect<{
      month: number;
      answers: Record<string, string>;
      current_index: number;
    }>(
      "exam_sessions",
      `student_id=eq.${encodeURIComponent(auth.sub)}&order=updated_at.desc&limit=1`
    );
    const exam = examRows[0] ?? null;

    // 3) Seviye tespit (month 0) yapılmış mı?
    const levelTestDone = await dbSelectOne<{ id: string }>(
      "exam_results",
      `student_id=eq.${encodeURIComponent(auth.sub)}&month=eq.0`
    );

    // 4) Öneri üret
    let suggestion: { title: string; detail: string; href: string } | null = null;

    if (exam) {
      const answered = Object.keys(exam.answers || {}).length;
      suggestion = {
        title: "Yarım kalmış denemen var",
        detail: `${exam.month === 0 ? "Seviye Tespit" : exam.month + ". Ay Denemesi"} — ${answered} soruyu işaretledin, kaldığın yerden devam et.`,
        href: `/aylik-denemeler?month=${exam.month}&resume=1`,
      };
    } else if (!levelTestDone) {
      suggestion = {
        title: "Önce seviyeni tespit edelim",
        detail:
          "Hoş geldin! 90 soruluk Seviye Tespit Sınavı ile başlayalım — sonuçların çalışma planını şekillendirecek.",
        href: "/aylik-denemeler?month=0",
      };
    } else if (study && study.solved > 0 && study.solved < study.target) {
      const kalan = study.target - study.solved;
      suggestion = {
        title: "Kaldığın yerden devam et",
        detail: `Bugün ${study.target} soruluk hedefin ${study.solved}'ini çözdün, ${kalan} soru kaldı.`,
        href: "/calis",
      };
    } else if (study && study.solved >= study.target) {
      suggestion = {
        title: "Bugünün hedefi tamam!",
        detail: `${study.target} soruyu bitirdin (${study.correct} doğru). Pekiştirme sayfasına göz atabilirsin.`,
        href: "/pekistirme",
      };
    } else {
      suggestion = {
        title: "Bugünkü çalışmana başla",
        detail: "24 soruluk günlük plan hazır — sıradaki sorudan başlayalım.",
        href: "/calis",
      };
    }

    return NextResponse.json({
      today: study ?? { solved: 0, correct: 0, target: 24, state: {} },
      exam,
      suggestion,
    });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}