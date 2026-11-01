import { NextRequest, NextResponse } from "next/server";
import { dbSelectOne, dbUpsert, dbDelete } from "../../../lib/db";
import { authFromRequest } from "../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Yarım kalmış denemeyi getir (kaldığın yerden devam et). */
export async function GET(request: NextRequest) {
  const auth = await authFromRequest(request);
  if (!auth) return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });

  const month = parseInt(request.nextUrl.searchParams.get("month") || "-1", 10);
  if (isNaN(month) || month < 0 || month > 11) {
    return NextResponse.json({ error: "Geçersiz ay." }, { status: 400 });
  }
  try {
    const row = await dbSelectOne(
      "exam_sessions",
      `student_id=eq.${encodeURIComponent(auth.sub)}&month=eq.${month}`
    );
    return NextResponse.json({ session: row });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}

/** Yarım kalmış denemeyi kaydet. */
export async function POST(request: NextRequest) {
  const auth = await authFromRequest(request);
  if (!auth) return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });

  try {
    const body = await request.json();
    const month = Number(body.month);
    if (isNaN(month) || month < 0 || month > 11) {
      return NextResponse.json({ error: "Geçersiz ay." }, { status: 400 });
    }
    await dbUpsert(
      "exam_sessions",
      {
        student_id: auth.sub,
        month,
        answers: body.answers ?? {},
        current_index: Math.max(0, Number(body.currentIndex) || 0),
        updated_at: new Date().toISOString(),
      },
      "student_id,month"
    );
    return NextResponse.json({ success: true });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}

/** Denemeyi tamamlandı say — yarım kalmış oturumu sil. */
export async function DELETE(request: NextRequest) {
  const auth = await authFromRequest(request);
  if (!auth) return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });

  const month = parseInt(request.nextUrl.searchParams.get("month") || "-1", 10);
  if (isNaN(month) || month < 0 || month > 11) {
    return NextResponse.json({ error: "Geçersiz ay." }, { status: 400 });
  }
  try {
    await dbDelete(
      "exam_sessions",
      `student_id=eq.${encodeURIComponent(auth.sub)}&month=eq.${month}`
    );
    return NextResponse.json({ success: true });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}