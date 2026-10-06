import { createHash, timingSafeEqual } from "node:crypto";
import questionRows from "../../../data/questions/questions.json";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const SOURCE_TYPES = ["REAL_LGS", "MEB_SAMPLE", "MEB_BOOK", "MEB_CURRICULUM", "VERIFIED_EXTERNAL", "AI_GENERATED"] as const;
const MEB_TYPES = new Set(["REAL_LGS", "MEB_SAMPLE", "MEB_BOOK", "MEB_CURRICULUM"]);
const REQUIRED_CHECKS = ["source_verified", "year_verified", "booklet_verified", "question_number_verified", "text_verified", "options_verified", "answer_key_source_verified", "answer_key_verified", "curriculum_verified", "solution_verified", "duplicate_checked"] as const;
const REPRESENTATIONS = ["STRUCTURED_TEXT", "IMAGE_BACKED", "HYBRID"] as const;
type SourceType = (typeof SOURCE_TYPES)[number];
type QuestionVisual = {
  publicPath: string; page: number;
  clipRectPt: { x0: number; y0: number; x1: number; y1: number };
  renderDpi: number; authority: "ORIGINAL_MEB_PDF";
};
type Question = {
  id: string; sourceId: string; sourceType: SourceType; year?: number; booklet?: string;
  subject: string; grade: 8; questionNumber: number;
  // Görsel-dominant (IMAGE_BACKED) satırlarda stem/options null olabilir; temsil
  // `visual` kanıtıyla taşınır. Eksik temsil kendiliğinden "geçerli soru" sayılmaz.
  stem: string | null; options: Record<string, string> | null;
  representation?: "STRUCTURED_TEXT" | "IMAGE_BACKED" | "HYBRID"; visual?: QuestionVisual | null;
  answer: string; solution: string; status: string; curriculum: {
    layer?: "LGS_REFERENCE_2018_PLUS" | "CURRENT_TYMM"; subject?: string; unit?: string;
    topic?: string; learningOutcome?: string; skill?: string; version?: string;
  };
  verification: Record<string, boolean>; sourceHash: string;
};

// Görsel temsilli kayıtlar yalnız yayın satırının kendi kanıtlı görsel alanıyla
// kabul edilir; stem/options yoksunluğu "görsel var" demek değildir.
const VISUAL_PATH = /^\/[a-z0-9]+(?:-[a-z0-9]+)*(?:\/[a-z0-9]+(?:-[a-z0-9]+)*)*\.png$/;

function validVisual(value: unknown): value is QuestionVisual {
  if (!value || typeof value !== "object") return false;
  const v = value as Partial<QuestionVisual>;
  if (v.authority !== "ORIGINAL_MEB_PDF") return false;
  if (typeof v.publicPath !== "string" || !VISUAL_PATH.test(v.publicPath) || v.publicPath.includes("..")) return false;
  if (!Number.isInteger(v.page) || (v.page as number) < 1) return false;
  if (!Number.isInteger(v.renderDpi) || (v.renderDpi as number) < 150) return false;
  const r = v.clipRectPt;
  return !!r && ["x0", "y0", "x1", "y1"].every((k) => typeof r[k as keyof typeof r] === "number");
}

function validQuestion(value: unknown): value is Question {
  if (!value || typeof value !== "object") return false;
  const q = value as Partial<Question>;
  const isMeb = MEB_TYPES.has(q.sourceType ?? "");
  const representation = q.representation ?? "STRUCTURED_TEXT";
  // Temsil değeri beyan edilmiş enum dışına çıkmamalı; aksi hâlde "bilinmeyen"
  // temsil yapılandırılmış kola düşer ve görsel kapısı sessizce atlanır.
  if (!REPRESENTATIONS.includes(representation as (typeof REPRESENTATIONS)[number])) return false;
  // Görsel ağırlıklı temsillerde gövde metni temsilin parçası değildir; her iki
  // temsilde de cevap anahtarı A-D olmalı ve sunucuda kalır.
  const stemOk = representation === "IMAGE_BACKED"
    ? q.stem === null || q.stem === undefined || q.stem === ""
    : typeof q.stem === "string" && q.stem.trim().length > 0;
  // Yapılandırılmış temsilde seçenekler zorunlu ve eksiksizdir; görsel temsilde
  // seçenekler soru görselinin içindedir, bu yüzden null kabul edilir.
  const optionsOk = representation === "IMAGE_BACKED"
    ? q.options === null || q.options === undefined || (typeof q.options === "object" && !Array.isArray(q.options))
    : !!q.options && typeof q.options === "object" && !Array.isArray(q.options);
  const visualOk = representation === "STRUCTURED_TEXT"
    ? q.visual === null || q.visual === undefined
    : validVisual(q.visual);
  return typeof q.id === "string" && typeof q.sourceId === "string" &&
    SOURCE_TYPES.includes(q.sourceType as SourceType) && q.status === "VERIFIED" &&
    !(q.sourceType === "REAL_LGS" && (!Number.isInteger(q.year) || (q.year as number) < 2018)) &&
    (!isMeb || q.sourceId.startsWith("MEB-")) && (q.sourceType !== "AI_GENERATED" || q.sourceId.startsWith("AI-")) &&
    q.grade === 8 && typeof q.subject === "string" && stemOk && optionsOk && visualOk &&
    typeof q.answer === "string" && /^[A-D]$/.test(q.answer) &&
    (representation === "IMAGE_BACKED" || Object.hasOwn(q.options ?? {}, q.answer)) && typeof q.solution === "string" &&
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
