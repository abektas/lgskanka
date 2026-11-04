import { NextRequest, NextResponse } from "next/server";
import { getExamManifest } from "../../../lib/exam-manifests";
import { dbInsert, dbDelete, dbSelect } from "../../../lib/db";
import { authFromRequest } from "../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

interface SubmitBody {
  month: number;
  answers: Record<string, string>; // questionId -> "A"|"B"|"C"|"D"
  studentId?: string;
}

export async function POST(request: NextRequest) {
  const auth = await authFromRequest(request);
  if (!auth) return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });

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

    const previousResults = await dbSelect(
      "exam_results",
      `student_id=eq.${encodeURIComponent(auth.sub)}&month=eq.${month}&order=completed_at.desc&limit=1`
    );
    if (previousResults.length > 0) {
      const previous = previousResults[0] as Record<string, unknown>;
      const savedDetails = Array.isArray(previous.details) ? previous.details : [];
      const publicDetails = savedDetails.map((detail: Record<string, unknown>) => {
        const { correct: _answerKey, ...safeDetail } = detail;
        return safeDetail;
      });
      return NextResponse.json({
        month: manifest.month,
        monthName: manifest.monthName,
        totalQuestions: manifest.totalQuestions,
        durationMinutes: manifest.durationMinutes,
        correct: Number(previous.correct) || 0,
        wrong: Number(previous.wrong) || 0,
        empty: Number(previous.empty) || 0,
        percentage: Number(previous.percentage) || 0,
        level: previous.level,
        bySubject: previous.by_subject,
        details: publicDetails,
        completedAt: previous.completed_at,
      });
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

    // Sonucu sunucuya kaydet ve yarım kalan oturumu temizle
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

    const publicDetails = details.map((detail) => {
      const { correct: _answerKey, ...safeDetail } = detail;
      return safeDetail;
    });

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
      details: publicDetails,
      completedAt: new Date().toISOString(),
    });
  } catch {
    return NextResponse.json(
      { error: "Değerlendirme başarısız" },
      { status: 500 }
    );
  }
}