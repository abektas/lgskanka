import { NextRequest, NextResponse } from "next/server";
import { dbSelectOne, dbUpsert } from "../../../lib/db";
import { authFromRequest } from "../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Günlük çalışma durumunu getir (bugün). */
export async function GET(request: NextRequest) {
  const auth = await authFromRequest(request);
  if (!auth) return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });

  const date = request.nextUrl.searchParams.get("date") || today();
  try {
    const row = await dbSelectOne(
      "study_sessions",
      `student_id=eq.${encodeURIComponent(auth.sub)}&session_date=eq.${date}`
    );
    return NextResponse.json({ session: row });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}

/** Günlük çalışma durumunu kaydet (kaldığın yerden devam et). */
export async function POST(request: NextRequest) {
  const auth = await authFromRequest(request);
  if (!auth) return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });

  try {
    const body = await request.json();
    const date = typeof body.date === "string" && body.date ? body.date : today();
    await dbUpsert(
      "study_sessions",
      {
        student_id: auth.sub,
        session_date: date,
        solved: Math.max(0, Number(body.solved) || 0),
        correct: Math.max(0, Number(body.correct) || 0),
        target: Math.max(1, Number(body.target) || 24),
        state: body.state ?? {},
        updated_at: new Date().toISOString(),
      },
      "student_id,session_date"
    );
    return NextResponse.json({ success: true });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}