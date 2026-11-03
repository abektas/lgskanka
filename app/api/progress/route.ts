import { NextRequest, NextResponse } from "next/server";
import { dbSelect, dbUpsert } from "../../../lib/db";
import { authFromRequest } from "../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

interface BadgeRow {
  badge_id: string;
  earned: boolean;
  earned_at: string | null;
  progress: number;
  updated_at: string;
}

interface WeeklyTestRow {
  date: string;
  total: number;
  correct: number;
  wrong: number;
  blank: number;
  by_category: Record<string, { total: number; correct: number }>;
  weak_units: unknown[];
  question_ids: string[];
  wrong_question_ids: string[];
}

/** Rozet ilerlemesini getir (sunucudan). */
export async function GET(request: NextRequest) {
  const auth = await authFromRequest(request);
  if (!auth) return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });

  const { searchParams } = request.nextUrl;
  const type = searchParams.get("type"); // "badges" | "weekly_tests"

  try {
    if (type === "badges") {
      const rows = await dbSelect<BadgeRow>(
        "badge_progress",
        `student_id=eq.${encodeURIComponent(auth.sub)}&order=badge_id`
      );
      const payload = rows.reduce<Record<string, { earned: boolean; earned_at: string | null; progress: number }>>((acc, r) => {
        acc[r.badge_id] = { earned: r.earned, earned_at: r.earned_at, progress: r.progress };
        return acc;
      }, {});
      return NextResponse.json({ badges: payload });
    }

    if (type === "weekly_tests") {
      const rows = await dbSelect<WeeklyTestRow>(
        "weekly_test_history",
        `student_id=eq.${encodeURIComponent(auth.sub)}&order=date.asc&limit=100`
      );
      return NextResponse.json({ weekly_tests: rows });
    }

    return NextResponse.json({ error: "type=badges|weekly_tests gerekli" }, { status: 400 });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}

/** Rozet veya haftalık test ilerlemesini kaydet (toplu upsert). */
export async function POST(request: NextRequest) {
  const auth = await authFromRequest(request);
  if (!auth) return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });

  try {
    const body = await request.json();
    const type = String(body?.type ?? ""); // "badges" | "weekly_tests"

    if (type === "badges") {
      const badges: Record<string, { earned: boolean; earned_at: string | null; progress: number }> = body?.badges ?? {};
      if (Object.keys(badges).length === 0) {
        return NextResponse.json({ error: "badges{} gerekli" }, { status: 400 });
      }

      const rows = Object.entries(badges).slice(0, 50).map(([badge_id, data]) => ({
        student_id: auth.sub,
        badge_id,
        earned: !!data.earned,
        earned_at: data.earned ? (data.earned_at ?? new Date().toISOString()) : null,
        progress: Math.max(0, Number(data.progress) || 0),
        updated_at: new Date().toISOString(),
      }));

      await dbUpsert("badge_progress", rows, "student_id,badge_id");
      return NextResponse.json({ success: true, count: rows.length });
    }

    if (type === "weekly_tests") {
      const tests: WeeklyTestRow[] = Array.isArray(body?.weekly_tests) ? body.weekly_tests : [];
      if (tests.length === 0) {
        return NextResponse.json({ error: "weekly_tests[] gerekli" }, { status: 400 });
      }

      const rows = tests.slice(0, 100).map((t) => ({
        student_id: auth.sub,
        date: t.date,
        total: Math.max(0, Number(t.total) || 0),
        correct: Math.max(0, Number(t.correct) || 0),
        wrong: Math.max(0, Number(t.wrong) || 0),
        blank: Math.max(0, Number(t.blank) || 0),
        by_category: t.by_category ?? {},
        weak_units: t.weak_units ?? [],
        question_ids: t.question_ids ?? [],
        wrong_question_ids: t.wrong_question_ids ?? [],
        created_at: t.date,
      }));

      await dbUpsert("weekly_test_history", rows, "student_id,date");
      return NextResponse.json({ success: true, count: rows.length });
    }

    return NextResponse.json({ error: "type=badges|weekly_tests gerekli" }, { status: 400 });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}