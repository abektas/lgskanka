import { NextRequest, NextResponse } from "next/server";
import { dbSelectOne, dbUpdate } from "../../../../lib/db";
import { hashPassword, normalizeUsername } from "../../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Şifresi sıfırlanan öğrencinin giriş yapacağı standart şifre. */
const STANDARD_PASSWORD = "1234";

/**
 * POST /api/auth/forgot — "Şifremi unuttum"
 *
 * Body: { "username": "ozge123" }
 * Şifreyi standart "1234" değerine sıfırlar; öğrenci hemen giriş yapabilir.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const username = normalizeUsername(body.username);

    if (!username) {
      return NextResponse.json({ error: "Kullanıcı adı gerekli." }, { status: 400 });
    }

    const student = await dbSelectOne<{ id: string }>(
      "students",
      `username=eq.${encodeURIComponent(username)}`
    );
    if (!student) {
      return NextResponse.json({ error: "Bu kullanıcı adı bulunamadı." }, { status: 404 });
    }

    const password_hash = await hashPassword(STANDARD_PASSWORD);
    await dbUpdate("students", `id=eq.${encodeURIComponent(student.id)}`, {
      password_hash,
    });

    return NextResponse.json({ success: true, username, newPassword: STANDARD_PASSWORD });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}