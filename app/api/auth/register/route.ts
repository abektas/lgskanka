import { NextRequest, NextResponse } from "next/server";
import { dbSelectOne, dbInsert, getStudentCount } from "../../../../lib/db";
import { hashPassword, signToken } from "../../../../lib/auth";
import { rateLimit, getClientIp } from "../../../../lib/rate-limit";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Ücretsiz katman koruması: en fazla 500 öğrenci kaydı
const MAX_STUDENTS = 500;

interface StudentRow {
  id: string;
  username: string;
  name: string;
  gender: string;
  variant: number;
  registered_at: string;
}

function normalizeUsername(raw: string): string {
  return raw
    .toLocaleLowerCase("tr-TR")
    .replace(/\s+/g, "")
    .replace(/[^a-z0-9._-]/g, "")
    .slice(0, 24);
}

export async function POST(request: NextRequest) {
  try {
    // Rate limit: IP başına dakikada 5 kayıt denemesi
    const ip = getClientIp(request);
    const rl = rateLimit(`register:${ip}`, 5, 60_000);
    if (!rl.allowed) {
      return NextResponse.json(
        { error: "Çok fazla deneme yaptın. Bir dakika sonra tekrar dene." },
        { status: 429 }
      );
    }

    const body = await request.json();
    const username = normalizeUsername(String(body.username ?? ""));
    const password = String(body.password ?? "");
    const name = String(body.name ?? "").trim().slice(0, 40);
    const gender = body.gender === "girl" ? "girl" : "boy";
    const variant = Math.max(0, Math.min(2, Number(body.variant) || 0));

    if (username.length < 3) {
      return NextResponse.json(
        { error: "Kullanıcı adı en az 3 karakter olmalı (harf, rakam, . _ -)." },
        { status: 400 }
      );
    }
    if (password.length < 4) {
      return NextResponse.json(
        { error: "Şifre en az 4 karakter olmalı." },
        { status: 400 }
      );
    }
    if (!name) {
      return NextResponse.json({ error: "İsim gerekli." }, { status: 400 });
    }

    // Ücretsiz katman koruması — öğrenci sayısı sınırı
    const studentCount = await getStudentCount();
    if (studentCount >= MAX_STUDENTS) {
      return NextResponse.json(
        { error: `Kayıt kapasitesi dolu (${MAX_STUDENTS} öğrenci). Lütfen öğretmeninle iletişime geç.` },
        { status: 403 }
      );
    }

    // Kullanıcı adı benzersiz mi?
    const existing = await dbSelectOne<StudentRow>(
      "students",
      `username=eq.${encodeURIComponent(username)}`
    );
    if (existing) {
      return NextResponse.json(
        { error: "Bu kullanıcı adı alınmış. Başka bir kullanıcı adı dene." },
        { status: 409 }
      );
    }

    const passwordHash = await hashPassword(password);
    const inserted = await dbInsert<StudentRow>("students", {
      username,
      password_hash: passwordHash,
      name,
      gender,
      variant,
      registered_at: new Date().toISOString(),
    });
    const student = inserted[0];
    if (!student) {
      return NextResponse.json({ error: "Kayıt oluşturulamadı." }, { status: 500 });
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
      { error: "Kayıt şu anda yapılamıyor.", detail: String(e).slice(0, 200) },
      { status: 500 }
    );
  }
}