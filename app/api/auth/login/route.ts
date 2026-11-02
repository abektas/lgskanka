import { NextRequest, NextResponse } from "next/server";
import { dbSelectOne } from "../../../../lib/db";
import { verifyPassword, signToken } from "../../../../lib/auth";
import { rateLimit, getClientIp } from "../../../../lib/rate-limit";

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
    // Rate limit: IP başına dakikada 10 giriş denemesi
    const ip = getClientIp(request);
    const rl = rateLimit(`login:${ip}`, 10, 60_000);
    if (!rl.allowed) {
      return NextResponse.json(
        { error: "Çok fazla deneme yaptın. Bir dakika sonra tekrar dene." },
        { status: 429 }
      );
    }

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