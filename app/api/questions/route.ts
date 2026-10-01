import { createHash, timingSafeEqual } from "node:crypto";
import questionRows from "../../../data/questions/questions.json";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const SOURCE_TYPES = ["REAL_LGS", "MEB_SAMPLE", "MEB_BOOK", "MEB_CURRICULUM", "VERIFIED_EXTERNAL", "AI_GENERATED"] as const;
const MEB_TYPES = new Set(["REAL_LGS", "MEB_SAMPLE", "MEB_BOOK", "MEB_CURRICULUM"]);
const REQUIRED_CHECKS = ["source_verified", "year_verified", "booklet_verified", "question_number_verified", "text_verified", "options_verified", "answer_key_source_verified", "answer_key_verified", "curriculum_verified", "solution_verified", "duplicate_checked"] as const;
type SourceType = (typeof SOURCE_TYPES)[number];
type Question = {
  id: string; sourceId: string; sourceType: SourceType; year?: number; booklet?: string;
  subject: string; grade: 8; questionNumber: number; stem: string; options: Record<string, string>;
  answer: string; solution: string; status: string; curriculum: {
    layer?: "LGS_REFERENCE_2018_PLUS" | "CURRENT_TYMM"; subject?: string; unit?: string;
    topic?: string; learningOutcome?: string; skill?: string; version?: string;
  };
  verification: Record<string, boolean>; sourceHash: string;
};

function validQuestion(value: unknown): value is Question {
  if (!value || typeof value !== "object") return false;
  const q = value as Partial<Question>;
  const isMeb = MEB_TYPES.has(q.sourceType ?? "");
  return typeof q.id === "string" && typeof q.sourceId === "string" &&
    SOURCE_TYPES.includes(q.sourceType as SourceType) && q.status === "VERIFIED" &&
    !(q.sourceType === "REAL_LGS" && (!Number.isInteger(q.year) || (q.year as number) < 2018)) &&
    (!isMeb || q.sourceId.startsWith("MEB-")) && (q.sourceType !== "AI_GENERATED" || q.sourceId.startsWith("AI-")) &&
    q.grade === 8 && typeof q.subject === "string" && typeof q.stem === "string" &&
    !!q.options && typeof q.options === "object" && !Array.isArray(q.options) &&
    typeof q.answer === "string" && Object.hasOwn(q.options, q.answer) && typeof q.solution === "string" &&
    /^[a-f0-9]{64}$/.test(q.sourceHash ?? "") && !!q.verification &&
    REQUIRED_CHECKS.every((key) => q.verification?.[key] === true) &&
    !!q.curriculum && ["LGS_REFERENCE_2018_PLUS", "CURRENT_TYMM"].includes(q.curriculum.layer ?? "") &&
    [q.curriculum.subject, q.curriculum.unit, q.curriculum.topic, q.curriculum.learningOutcome, q.curriculum.skill, q.curriculum.version].every((part) => typeof part === "string" && part.trim().length > 0);
}

function readQuestions(): Question[] {
  const records: unknown = questionRows;
  if (!Array.isArray(records)) return [];
  return records.filter(validQuestion);
}

function toPublicQuestion(q: Question) {
  const { answer: _answer, verification: _verification, sourceHash: _hash, ...publicQuestion } = q;
  return publicQuestion;
}

export async function GET(request: NextRequest) {
  try {
    const subject = request.nextUrl.searchParams.get("subject");
    const layer = request.nextUrl.searchParams.get("layer");
    const questions = readQuestions();
    const items = questions.filter((q) => (!subject || q.subject === subject) && (!layer || q.curriculum.layer === layer));
    return NextResponse.json({ items: items.map(toPublicQuestion), count: items.length }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ error: "Soru bankası şu anda kullanılamıyor." }, { status: 503, headers: { "Cache-Control": "no-store" } });
  }
}

export async function POST(request: NextRequest) {
  let body: unknown;
  try { body = await request.json(); } catch { return NextResponse.json({ error: "Geçersiz JSON gövdesi." }, { status: 400 }); }
  if (!body || typeof body !== "object") return NextResponse.json({ error: "Geçersiz istek." }, { status: 400 });
  const { questionId, answer } = body as Record<string, unknown>;
  if (typeof questionId !== "string" || questionId.length > 200 || typeof answer !== "string" || answer.length > 20) {
    return NextResponse.json({ error: "questionId ve answer alanları gerekli." }, { status: 400 });
  }
  try {
    const question = (readQuestions()).find((q) => q.id === questionId);
    if (!question) return NextResponse.json({ error: "Soru bulunamadı veya kullanıma açık değil." }, { status: 404 });
    const submitted = createHash("sha256").update(answer).digest();
    const expected = createHash("sha256").update(question.answer).digest();
    return NextResponse.json({ correct: timingSafeEqual(submitted, expected) }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ error: "Soru bankası şu anda kullanılamıyor." }, { status: 503, headers: { "Cache-Control": "no-store" } });
  }
}
