import { NextRequest, NextResponse } from "next/server";
import { dbSelect, dbInsert } from "../../../lib/db";
import { authFromRequest } from "../../../lib/auth";
import { isAdminRequest } from "../../../lib/admin";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

interface ReportBody {
  source?: string;
  month?: number;
  monthName?: string;
  questionId?: string;
  questionNumber?: number;
  subject?: string;
  imagePath?: string;
  reason?: string;
}

/**
 * POST /api/question-reports — öğrenci "Soru eksik veya bozuk" bildirimi gönderir.
 * GET  /api/question-reports — öğretmen (admin anahtarıyla) tüm bildirimleri listeler.
 */
export async function POST(request: NextRequest) {
  const auth = await authFromRequest(request);
  if (!auth) return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });

  try {
    const body = (await request.json()) as ReportBody;
    if (!body?.questionId) {
      return NextResponse.json({ error: "questionId gerekli." }, { status: 400 });
    }

    // Aynı öğrenci aynı soruyu tekrar bildirmesin
    const existing = await dbSelect<{ id: string }>(
      "question_reports",
      `student_id=eq.${encodeURIComponent(auth.sub)}&question_id=eq.${encodeURIComponent(body.questionId)}&source=eq.${encodeURIComponent(body.source || "deneme")}`
    );
    if (existing.length > 0) {
      return NextResponse.json({ success: true, duplicate: true });
    }

    await dbInsert("question_reports", {
      student_id: auth.sub,
      source: body.source || "deneme",
      month: body.month ?? null,
      month_name: body.monthName ?? null,
      question_id: body.questionId,
      question_number: body.questionNumber ?? null,
      subject: body.subject ?? null,
      image_path: body.imagePath ?? null,
      reason: body.reason ?? null,
      status: "acik",
      created_at: new Date().toISOString(),
    });
    return NextResponse.json({ success: true });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}

/** Öğretmen: bildirim listesi (öğrenci adıyla birlikte). */
export async function GET(request: NextRequest) {
  if (!isAdminRequest(request)) {
    return NextResponse.json({ error: "Yetkisiz. Öğretmen anahtarı gerekli." }, { status: 401 });
  }
  try {
    const rows = await dbSelect(
      "question_reports",
      "order=created_at.desc&limit=200",
      "*,students(name,username)"
    );
    return NextResponse.json({ reports: rows });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}