import { NextRequest, NextResponse } from "next/server";
import { dbSelect, dbUpsert } from "../../../lib/db";
import { authFromRequest } from "../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

interface RecordBody {
  questionId: string;
  subject: string;
  unit: number | null;
  unitName: string | null;
  topic: string | null;
  selectedAnswer: string;
  correct: boolean;
  errorReasonCode: string | null;
  timeSpentSec: number;
  source?: string;
  createdAt: string;
}

/** Cevap kayıtlarını getir. */
export async function GET(request: NextRequest) {
  const auth = await authFromRequest(request);
  if (!auth) return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });

  const { searchParams } = request.nextUrl;
  const limit = Math.min(2000, parseInt(searchParams.get("limit") || "1000", 10));
  try {
    const rows = await dbSelect(
      "answer_records",
      `student_id=eq.${encodeURIComponent(auth.sub)}&order=created_at.desc&limit=${limit}`
    );
    return NextResponse.json(rows);
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}

/** Cevap kayıtları yükle (toplu). */
export async function POST(request: NextRequest) {
  const auth = await authFromRequest(request);
  if (!auth) return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });

  try {
    const body = await request.json();
    const records: RecordBody[] = Array.isArray(body?.records) ? body.records : [];
    if (records.length === 0) {
      return NextResponse.json({ error: "records[] gerekli." }, { status: 400 });
    }
    const rows = records.slice(0, 200).map((r) => ({
      student_id: auth.sub,
      question_id: r.questionId,
      subject: r.subject,
      unit: r.unit ?? null,
      unit_name: r.unitName ?? null,
      topic: r.topic ?? null,
      selected_answer: r.selectedAnswer ?? "",
      correct: !!r.correct,
      error_reason_code: r.errorReasonCode ?? null,
      time_spent_sec: Math.max(0, Number(r.timeSpentSec) || 0),
      source: r.source || "gunluk",
      created_at: r.createdAt || new Date().toISOString(),
    }));

    await dbUpsert("answer_records", rows, "student_id,question_id,source");
    return NextResponse.json({ success: true, count: rows.length });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}