import { NextRequest, NextResponse } from "next/server";
import { createHash, timingSafeEqual } from "node:crypto";

const R2_PUBLIC_URL = "https://pub-782be99090dc4f8586da5bf5d073c4a5.r2.dev";

interface StudyQuestion {
  id: string;
  subject: string;
  sourceBook: string;
  questionNumber: number;
  page: number;
  imagePath: string | null;
  answer: string | null;
  unit: number | null;
  unitName: string | null;
  section: string | null;
  questionText: string | null;
  topic: string | null;
  learningOutcomeCode: string | null;
  learningOutcomeText: string | null;
  pedagogicalDifficulty: number | null;
  difficultyConfidence: string | null;
  skill: string | null;
  questionType: string | null;
  analysisStatus: string | null;
}

async function fetchJson(url: string): Promise<any> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch ${url}: ${res.status}`);
  return res.json();
}

/** local PNG filename -> R2 webp path (e.g. "turkce/official/abc123.webp") */
async function loadImageMap(): Promise<Map<string, string>> {
  const raw = await fetchJson(`${R2_PUBLIC_URL}/study_manifests/image_map.json`);
  const result = new Map<string, string>();
  for (const [localPath, info] of Object.entries(raw as Record<string, any>)) {
    const name = localPath.split("/").pop();
    const webpPath = info?.webp_path;
    if (name && webpPath) {
      const r2Key = webpPath.replace(/^.*?\/webp\//, "");
      result.set(name, r2Key);
    }
  }
  return result;
}

async function loadAllQuestions(imageMap: Map<string, string>): Promise<StudyQuestion[]> {
  const index = await fetchJson(`${R2_PUBLIC_URL}/study_manifests/manifests_index.json`);
  const questions: StudyQuestion[] = [];

  for (const manifestKey of index.manifests) {
    const manifest = await fetchJson(`${R2_PUBLIC_URL}/${manifestKey}`);
    for (const q of manifest.questions || []) {
      const qnum = q.q || q.questionNumber;
      if (!qnum) continue;
      if (q.published === false) continue;
      if (q.cancelledInSource) continue;

      const originalFile = q.file || `q-${String(qnum).padStart(2, "0")}.png`;
      const webpPath = imageMap.get(originalFile);
      const imagePath = webpPath ? `${R2_PUBLIC_URL}/${webpPath}` : null;

      const mebiMatch = originalFile.match(/^mebi/i);
      const bookMatch = originalFile.match(/^((?:cal|nuli|mu|tu)\\d+)/i);
      const sourceBook = mebiMatch ? "MEBI" : bookMatch ? bookMatch[1].toUpperCase() : "UNKNOWN";

      questions.push({
        id:
          q.id ||
          `STUDY-${(q.subject || "UNKNOWN").toUpperCase()}-${originalFile
            .replace(/\.png$/i, "")
            .toUpperCase()}`,
        subject: q.subject || "UNKNOWN",
        sourceBook,
        questionNumber: qnum,
        page: q.page || 0,
        imagePath,
        answer: q.answer || null,
        unit: q.unit || null,
        unitName: q.unitName || null,
        section: q.section || null,
        questionText: q.questionText || null,
        topic: null,
        learningOutcomeCode: null,
        learningOutcomeText: null,
        pedagogicalDifficulty: null,
        difficultyConfidence: null,
        skill: null,
        questionType: null,
        analysisStatus: null,
      });
    }
  }
  return questions;
}

let questionsCache: StudyQuestion[] | null = null;

async function getQuestions(): Promise<StudyQuestion[]> {
  if (questionsCache) return questionsCache;
  const imageMap = await loadImageMap();
  questionsCache = await loadAllQuestions(imageMap);
  return questionsCache;
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;
    const subject = searchParams.get("subject");
    const unit = searchParams.get("unit");
    const limit = parseInt(searchParams.get("limit") || "0", 10);
    const wrongMode = searchParams.get("wrong_mode");
    const sort = searchParams.get("sort") || "unit_difficulty";

    let questions = await getQuestions();

    if (subject) {
      questions = questions.filter((q) => q.subject === subject);
    }
    if (unit) {
      questions = questions.filter((q) => q.unit === parseInt(unit, 10));
    }

    if (sort === "unit_difficulty") {
      questions.sort((a, b) => {
        const unitA = a.unit ?? 999;
        const unitB = b.unit ?? 999;
        if (unitA !== unitB) return unitA - unitB;
        const diffA = a.pedagogicalDifficulty ?? 999;
        const diffB = b.pedagogicalDifficulty ?? 999;
        return diffA - diffB;
      });
    }

    if (limit > 0) {
      questions = questions.slice(0, limit);
    }

    const publicQuestions = questions.map((q) => {
      if (wrongMode === "true") {
        return q;
      }
      const { answer, ...rest } = q;
      return rest;
    });

    return NextResponse.json(
      { items: publicQuestions, count: publicQuestions.length },
      { headers: { "Cache-Control": "no-store" } }
    );
  } catch {
    return NextResponse.json(
      { error: "Çalışma verisi şu anda kullanılamıyor." },
      { status: 503, headers: { "Cache-Control": "no-store" } }
    );
  }
}

export async function POST(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Geçersiz JSON gövdesi." }, { status: 400 });
  }
  if (!body || typeof body !== "object") {
    return NextResponse.json({ error: "Geçersiz istek." }, { status: 400 });
  }
  const { id, answer } = body as Record<string, unknown>;
  if (
    typeof id !== "string" ||
    id.length > 200 ||
    typeof answer !== "string" ||
    !/^[A-D]$/.test(answer)
  ) {
    return NextResponse.json({ error: "id ve answer (A-D) alanları gerekli." }, { status: 400 });
  }
  try {
    const questions = await getQuestions();
    const question = questions.find((q) => q.id === id);
    if (!question || !question.answer) {
      return NextResponse.json(
        { error: "Soru bulunamadı." },
        { status: 404, headers: { "Cache-Control": "no-store" } }
      );
    }
    const submitted = createHash("sha256").update(answer).digest();
    const expected = createHash("sha256").update(question.answer).digest();
    return NextResponse.json(
      { correct: timingSafeEqual(submitted, expected) },
      { headers: { "Cache-Control": "no-store" } }
    );
  } catch {
    return NextResponse.json(
      { error: "Çalışma verisi şu anda kullanılamıyor." },
      { status: 503, headers: { "Cache-Control": "no-store" } }
    );
  }
}
