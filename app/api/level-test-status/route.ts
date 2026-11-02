import { NextRequest, NextResponse } from "next/server";
import { authFromRequest } from "../../../lib/auth";
import { getLevelTestResult } from "../../../lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * GET /api/level-test-status
 * Seviye tespit sınavının tamamlanıp tamamlanmadığını kontrol eder.
 * Yerel localStorage kaybı durumunda sunucu tarafı doğrulama sağlar.
 */
export async function GET(request: NextRequest) {
  try {
    const auth = await authFromRequest(request);
    if (!auth) {
      return NextResponse.json({ completed: false, reason: "unauthenticated" });
    }

    const result = await getLevelTestResult(auth.sub);
    const completed = !!result;

    return NextResponse.json({
      completed,
      completedAt: completed ? (result as Record<string, unknown>)?.completed_at : null,
    });
  } catch (e) {
    return NextResponse.json(
      { completed: false, error: String(e).slice(0, 200) },
      { status: 500 }
    );
  }
}