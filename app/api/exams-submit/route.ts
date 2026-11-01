import { NextRequest, NextResponse } from "next/server";
import { getExamManifest } from "../../../lib/exam-manifests";
import { dbInsert, dbDelete } from "../../../lib/db";
import { authFromRequest } from "../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

interface SubmitBody {
  month: number;
  answers: Record<string, string>; // questionId -> "A"|"B"|"C"|"D"
  studentId?: string;
}

export async function POST(request: NextRequest) {
  try {
    const body: SubmitBody = await request.json();
    const { month, answers } = body;

    if (typeof month !== "number" || month < 0 || month > 11) {
      return NextResponse.json({ error: "Geçersiz ay" }, { status: 400 });
    }

    const manifest = getExamManifest(month);
    if (!manifest) {
      return NextResponse.json({ error: "Sınav bulunamadı" }, { status: 404 });
    }

    let correct = 0;
    let wrong = 0;
    let empty = 0;
    const bySubject: Record<string, { correct: number; wrong: number; empty: number; total: number }> = {};
    const details: Array<{
      questionId: string;
      subject: string;
      given: string | null;
      correct: string | null;
      isCorrect: boolean;
      topic: string | null;
      unit: number | null;
      difficultyScore: number;
    }> = [];

    for (const q of manifest.questions) {
      const given = answers[q.id] || null;
      const correctAns = q.answer || null;
      const subj = q.subject;

      if (!bySubject[subj]) {
        bySubject[subj] = { correct: 0, wrong: 0, empty: 0, total: 0 };
      }
      bySubject[subj].total++;

      let isCorrect = false;
      if (given === null || given === "") {
        empty++;
        bySubject[subj].empty++;
      } else if (given === correctAns) {
        correct++;
        bySubject[subj].correct++;
        isCorrect = true;
      } else {
        wrong++;
        bySubject[subj].wrong++;
      }

      details.push({
        questionId: q.id,
        subject: subj,
        given,
        correct: correctAns,
        isCorrect,
        topic: q.topic,
        unit: q.unit,
        difficultyScore: q.difficultyScore,
      });
    }

    const percentage = Math.round((correct / manifest.totalQuestions) * 100);
    let level = "Başlangıç";
    if (percentage >= 85) level = "İleri";
    else if (percentage >= 70) level = "Orta-İleri";
    else if (percentage >= 55) level = "Orta";
    else if (percentage >= 40) level = "Temel";

    // Sonucu sunucuya kaydet (giriş yapılmışsa) ve yarım kalan oturumu temizle
    const auth = await authFromRequest(request);
    if (auth) {
      try {
        await dbInsert("exam_results", {
          student_id: auth.sub,
          month: manifest.month,
          month_name: manifest.monthName,
          correct,
          wrong,
          empty,
          percentage,
          level,
          by_subject: bySubject,
          details,
          completed_at: new Date().toISOString(),
        });
        await dbDelete(
          "exam_sessions",
          `student_id=eq.${encodeURIComponent(auth.sub)}&month=eq.${month}`
        );
      } catch {
        // Kayıt hatası değerlendirmeyi engellemez
      }
    }

    return NextResponse.json({
      month: manifest.month,
      monthName: manifest.monthName,
      totalQuestions: manifest.totalQuestions,
      durationMinutes: manifest.durationMinutes,
      correct,
      wrong,
      empty,
      percentage,
      level,
      bySubject,
      details,
      completedAt: new Date().toISOString(),
    });
  } catch {
    return NextResponse.json(
      { error: "Değerlendirme başarısız" },
      { status: 500 }
    );
  }
}