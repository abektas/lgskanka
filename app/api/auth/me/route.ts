import { NextRequest, NextResponse } from "next/server";
import { dbSelectOne, dbUpdate } from "../../../../lib/db";
import { authFromRequest, hashPassword } from "../../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

interface StudentRow {
  id: string;
  username: string;
  name: string;
  gender: string;
  variant: number;
  registered_at: string;
}

function toPublic(s: StudentRow) {
  return {
    id: s.id,
    username: s.username,
    name: s.name,
    gender: s.gender,
    variant: s.variant,
    registeredAt: s.registered_at,
  };
}

/** Oturumdaki öğrenciyi getir. */
export async function GET(request: NextRequest) {
  const auth = await authFromRequest(request);
  if (!auth) {
    return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });
  }
  try {
    const student = await dbSelectOne<StudentRow>(
      "students",
      `id=eq.${encodeURIComponent(auth.sub)}`
    );
    if (!student) {
      return NextResponse.json({ error: "Öğrenci bulunamadı." }, { status: 404 });
    }
    return NextResponse.json({ student: toPublic(student) });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}

/** Profil güncelle (isim, karakter, şifre). */
export async function PATCH(request: NextRequest) {
  const auth = await authFromRequest(request);
  if (!auth) {
    return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });
  }
  try {
    const body = await request.json();
    const patch: Record<string, unknown> = {};

    if (typeof body.name === "string" && body.name.trim()) {
      patch.name = body.name.trim().slice(0, 40);
    }
    if (body.gender === "boy" || body.gender === "girl") {
      patch.gender = body.gender;
    }
    if (body.variant !== undefined) {
      patch.variant = Math.max(0, Math.min(2, Number(body.variant) || 0));
    }
    if (typeof body.password === "string" && body.password.length >= 4) {
      patch.password_hash = await hashPassword(body.password);
    }
    if (Object.keys(patch).length === 0) {
      return NextResponse.json({ error: "Güncellenecek alan yok." }, { status: 400 });
    }

    await dbUpdate("students", `id=eq.${encodeURIComponent(auth.sub)}`, patch);
    const student = await dbSelectOne<StudentRow>(
      "students",
      `id=eq.${encodeURIComponent(auth.sub)}`
    );
    return NextResponse.json({ student: student ? toPublic(student) : null });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}