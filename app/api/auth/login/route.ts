import { NextRequest, NextResponse } from "next/server";
import { dbSelectOne } from "../../../../lib/db";
import { verifyPassword, signToken } from "../../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

interface StudentRow {
  id: string;
  username: string;
  password_hash: string;
  name: string;
  gender: string;
  variant: number;
  registered_at: string;
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const username = String(body.username ?? "")
      .toLocaleLowerCase("tr-TR")
      .replace(/\s+/g, "");
    const password = String(body.password ?? "");

    if (!username || !password) {
      return NextResponse.json(
        { error: "Kullanıcı adı ve şifre gerekli." },
        { status: 400 }
      );
    }

    const student = await dbSelectOne<StudentRow>(
      "students",
      `username=eq.${encodeURIComponent(username)}`
    );
    if (!student) {
      return NextResponse.json(
        { error: "Kullanıcı adı veya şifre hatalı." },
        { status: 401 }
      );
    }

    const ok = await verifyPassword(password, student.password_hash);
    if (!ok) {
      return NextResponse.json(
        { error: "Kullanıcı adı veya şifre hatalı." },
        { status: 401 }
      );
    }

    const token = await signToken({
      sub: student.id,
      username: student.username,
      name: student.name,
    });

    return NextResponse.json({
      token,
      student: {
        id: student.id,
        username: student.username,
        name: student.name,
        gender: student.gender,
        variant: student.variant,
        registeredAt: student.registered_at,
      },
    });
  } catch (e) {
    return NextResponse.json(
      { error: "Giriş şu anda yapılamıyor.", detail: String(e).slice(0, 200) },
      { status: 500 }
    );
  }
}