import { NextRequest, NextResponse } from "next/server";
import { questionBank } from "../../../../data/content";

type SpeedQuestion = {
  id: string;
  subject: string;
  topic: string;
  text: string;
  options: string[];
  correctIndex: number;
};

function toSpeedQuestion(q: typeof questionBank[number]): SpeedQuestion {
  return {
    id: q.id,
    subject: q.subject,
    topic: q.topic,
    text: q.text,
    options: q.options,
    correctIndex: q.correct,
  };
}

export async function POST(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Geçersiz istek." }, { status: 400 });
  }

  const input = (body ?? {}) as Record<string, unknown>;

  if (input.mode === "batch") {
    const count = typeof input.count === "number" ? Math.min(input.count, 20) : 20;
    const excluded = Array.isArray(input.exclude)
      ? input.exclude.filter((id): id is string => typeof id === "string").slice(0, questionBank.length)
      : [];
    const pool = questionBank.filter((question) => !excluded.includes(question.id));
    const selected = pool.sort(() => Math.random() - 0.5).slice(0, count).map(toSpeedQuestion);
    return NextResponse.json({ questions: selected });
  }

  if (input.mode === "answer") {
    const questionId = typeof input.questionId === "string" ? input.questionId : "";
    const selectedIndex = input.selectedIndex;
    const question = questionBank.find((item) => item.id === questionId);
    if (!question || !Number.isInteger(selectedIndex) || (selectedIndex as number) < 0 || (selectedIndex as number) >= question.options.length) {
      return NextResponse.json({ error: "Soru veya seçenek geçersiz." }, { status: 400 });
    }
    const correct = selectedIndex === question.correct;
    return NextResponse.json({
      correct,
      correctIndex: question.correct,
      explanation: question.explain,
    });
  }

  return NextResponse.json({ error: "İşlem tanınmadı." }, { status: 400 });
}