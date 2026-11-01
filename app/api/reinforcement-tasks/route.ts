import { NextRequest, NextResponse } from "next/server";
import { dbSelect, dbUpsert } from "../../../lib/db";
import { authFromRequest } from "../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Pekiştirme görevlerini getir. */
export async function GET(request: NextRequest) {
  const auth = await authFromRequest(request);
  if (!auth) return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });

  try {
    const rows = await dbSelect(
      "reinforcement_tasks",
      `student_id=eq.${encodeURIComponent(auth.sub)}&order=created_at.desc`
    );
    return NextResponse.json(rows);
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}

/** Pekiştirme görevlerini kaydet (toplu upsert). */
export async function POST(request: NextRequest) {
  const auth = await authFromRequest(request);
  if (!auth) return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });

  try {
    const body = await request.json();
    const tasks: Array<Record<string, unknown>> = Array.isArray(body?.tasks)
      ? body.tasks
      : [];
    if (tasks.length === 0) {
      return NextResponse.json({ error: "tasks[] gerekli." }, { status: 400 });
    }

    const rows = tasks.slice(0, 100).map((t) => ({
      id: String(t.id),
      student_id: auth.sub,
      subject: String(t.subject ?? ""),
      unit: t.unit ?? null,
      unit_name: t.unitName ?? null,
      topic: String(t.topic ?? ""),
      source: String(t.source ?? "gunluk"),
      wrong_count: Math.max(0, Number(t.wrongCount) || 0),
      question_ids: t.questionIds ?? [],
      answers: t.answers ?? {},
      correctness: t.correctness ?? {},
      status: String(t.status ?? "bekliyor"),
      updated_at: new Date().toISOString(),
    }));

    await dbUpsert("reinforcement_tasks", rows, "id,student_id");
    return NextResponse.json({ success: true, count: rows.length });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}