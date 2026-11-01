import { NextRequest, NextResponse } from "next/server";
import {
  getExamManifest,
  listExamMonths,
  toPublicQuestion,
} from "../../../lib/exam-manifests";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;
    const monthParam = searchParams.get("month");
    const subject = searchParams.get("subject");
    const listOnly = searchParams.get("list") === "true";

    // Sadece mevcut ayları listele
    if (listOnly) {
      return NextResponse.json({ months: listExamMonths() });
    }

    // Belirli bir ay
    if (!monthParam) {
      return NextResponse.json(
        { error: "month parametresi gerekli" },
        { status: 400 }
      );
    }

    const month = parseInt(monthParam, 10);
    if (isNaN(month) || month < 0 || month > 11) {
      return NextResponse.json(
        { error: "Geçersiz ay (0-11)" },
        { status: 400 }
      );
    }

    const manifest = getExamManifest(month);
    if (!manifest) {
      return NextResponse.json(
        { error: "Bu ay için sınav bulunamadı" },
        { status: 404 }
      );
    }

    let questions = manifest.questions;

    if (subject) {
      questions = questions.filter((q) => q.subject === subject);
    }

    // Cevap anahtarı asla istemciye gitmez
    const publicQuestions = questions.map((q) =>
      toPublicQuestion(q, manifest.monthName)
    );

    return NextResponse.json(
      {
        month: manifest.month,
        monthName: manifest.monthName,
        durationMinutes: manifest.durationMinutes,
        subjectDurations: manifest.subjectDurations ?? null,
        totalQuestions: publicQuestions.length,
        items: publicQuestions,
      },
      { headers: { "Cache-Control": "no-store" } }
    );
  } catch {
    return NextResponse.json(
      { error: "Sınav verisi şu anda kullanılamıyor." },
      { status: 503, headers: { "Cache-Control": "no-store" } }
    );
  }
}