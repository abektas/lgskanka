import { NextRequest, NextResponse } from "next/server";
import { createHash } from "crypto";
import { questionBank } from "../../../../data/content";

type RunnerQuestion = (typeof questionBank)[number];

function publicQuestion(question: RunnerQuestion) {
  return {
    id: question.id,
    subject: question.subject,
    topic: question.topic,
    text: question.text,
    options: question.options,
  };
}

function timingSafeEqual(a: string, b: string): boolean {
  const ha = createHash("sha256").update(a).digest();
  const hb = createHash("sha256").update(b).digest();
  if (ha.length !== hb.length) return false;
  let diff = 0;
  for (let i = 0; i < ha.length; i++) diff |= ha[i] ^ hb[i];
  return diff === 0;
}

export async function POST(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Geçersiz istek." }, { status: 400 });
  }

  const input = (body ?? {}) as Record<string, unknown>;
  if (input.mode === "next") {
    const excluded = Array.isArray(input.exclude)
      ? input.exclude.filter((id): id is string => typeof id === "string").slice(0, questionBank.length)
      : [];
    const pool = questionBank.filter((question) => !excluded.includes(question.id));
    const selected = pool[Math.floor(Math.random() * pool.length)] ?? questionBank[0];
    return NextResponse.json({ question: publicQuestion(selected) });
  }

  if (input.mode === "answer") {
    const questionId = typeof input.questionId === "string" ? input.questionId : "";
    const selectedIndex = input.selectedIndex;
    const question = questionBank.find((item) => item.id === questionId);
    if (!question || !Number.isInteger(selectedIndex) || (selectedIndex as number) < 0 || (selectedIndex as number) >= question.options.length) {
      return NextResponse.json({ error: "Soru veya seçenek geçersiz." }, { status: 400 });
    }
    // Hash-based verification: correctIndex is NEVER sent to the client.
    const submittedHash = typeof input.answerHash === "string" ? input.answerHash : "";
    const expectedHash = createHash("sha256")
      .update(`${question.id}:${question.correct}`)
      .digest("hex");
    const correct = timingSafeEqual(submittedHash, expectedHash);
    return NextResponse.json({
      correct,
      explanation: question.explain,
    });
  }

  return NextResponse.json({ error: "İşlem tanınmadı." }, { status: 400 });
}
