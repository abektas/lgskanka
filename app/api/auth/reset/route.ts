import { NextRequest, NextResponse } from "next/server";
import { dbSelectOne, dbUpdate } from "../../../../lib/db";
import { hashPassword, normalizeUsername } from "../../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * Öğretmen için şifre sıfırlama.
 *
 * Kullanım: POST /api/auth/reset
 * Header:  x-admin-secret: <ADMIN_RESET_SECRET>
 * Body:    { "username": "ozge123", "newPassword": "yeni-sifre" }
 *
 * ADMIN_RESET_SECRET ortam değişkeninde saklanır (Worker secret).
 */
export async function POST(request: NextRequest) {
  const adminSecret = process.env.ADMIN_RESET_SECRET;
  const provided = request.headers.get("x-admin-secret") || "";
  if (!adminSecret || provided !== adminSecret) {
    return NextResponse.json({ error: "Yetki yok." }, { status: 403 });
  }

  try {
    const body = await request.json();
    const username = normalizeUsername(body.username);
    const newPassword = String(body.newPassword ?? "");

    if (!username || newPassword.length < 4) {
      return NextResponse.json(
        { error: "username ve en az 4 karakterli newPassword gerekli." },
        { status: 400 }
      );
    }

    const student = await dbSelectOne<{ id: string }>(
      "students",
      `username=eq.${encodeURIComponent(username)}`
    );
    if (!student) {
      return NextResponse.json({ error: "Öğrenci bulunamadı." }, { status: 404 });
    }

    const password_hash = await hashPassword(newPassword);
    await dbUpdate("students", `id=eq.${encodeURIComponent(student.id)}`, {
      password_hash,
    });

    return NextResponse.json({ success: true, username });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}