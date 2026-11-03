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
    const target = Math.max(1, Number(body.target) || 24);
    const solved = Math.max(0, Number(body.solved) || 0);
    const correct = Math.max(0, Number(body.correct) || 0);
    const incomingState =
      body.state && typeof body.state === "object" ? (body.state as Record<string, unknown>) : {};

    // Sayaçlar geriye gitmez: yarışan (ateşle-unut) push'larda eski değer yeniyi ezmesin.
    const existing = await dbSelectOne<{
      solved: number;
      correct: number;
      state: Record<string, unknown>;
    }>(
      "study_sessions",
      `student_id=eq.${encodeURIComponent(auth.sub)}&session_date=eq.${date}`
    );
    const prevSolved = Number(existing?.solved) || 0;
    const useIncoming = solved >= prevSolved;
    const finalSolved = Math.max(prevSolved, solved);
    const finalCorrect = useIncoming ? correct : Number(existing?.correct) || 0;
    const prevState = (existing?.state ?? {}) as Record<string, unknown>;
    // "Tamamlandı" bir kez true olunca geri alınmaz.
    const completed =
      prevState.completed === true || incomingState.completed === true || finalSolved >= target;

    await dbUpsert(
      "study_sessions",
      {
        student_id: auth.sub,
        session_date: date,
        solved: finalSolved,
        correct: finalCorrect,
        target,
        state: {
          ...prevState,
          ...incomingState,
          lastIndex: useIncoming
            ? incomingState.lastIndex ?? prevState.lastIndex
            : prevState.lastIndex,
          completed,
        },
        updated_at: new Date().toISOString(),
      },
      "student_id,session_date"
    );
    return NextResponse.json({ success: true, solved: finalSolved, completed });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}