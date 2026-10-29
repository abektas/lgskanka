import { NextRequest, NextResponse } from "next/server";
import { createHash, timingSafeEqual } from "node:crypto";
import { readdirSync, readFileSync, existsSync } from "fs";
import path from "path";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const STUDY_BASE = path.join(process.cwd(), "public", "study");
// Workspace folder is the source of truth; override with STUDY_DATA_DIR if needed.
const MANIFEST_BASE =
  process.env.STUDY_DATA_DIR || path.join(process.cwd(), "lgs_çalışma_soruları");

interface StudyQuestion {
  id: string;
  subject: string;
  sourceBook: string;
  questionNumber: number;
  page: number;
  imagePath: string;
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

interface AnalysisInfo {
  topic: string | null;
  learningOutcomeCode: string | null;
  learningOutcomeText: string | null;
  pedagogicalDifficulty: number | null;
  difficultyConfidence: string | null;
  skill: string | null;
  questionType: string | null;
  analysisStatus: string | null;
}

function loadAnalysisIndex(subjPath: string): Map<string, AnalysisInfo> {
  const index = new Map<string, AnalysisInfo>();
  const analysisFiles = ["analysis.jsonl", ...readdirSync(subjPath).filter((f) => /^analysis_mebi.*\.jsonl$/i.test(f))];
  for (const af of analysisFiles) {
    const ap = path.join(subjPath, af);
    if (!existsSync(ap)) continue;
    try {
      const lines = readFileSync(ap, "utf-8").split("\n").filter(Boolean);
      for (const line of lines) {
        try {
          const a = JSON.parse(line);
          const key = path.basename(a.file || "");
          if (!key) continue;
          // İlk (tam analiz) kayıt öncelikli; aday eşleştirme yalnızca boşsa doldurur
          if (index.has(key) && index.get(key)!.learningOutcomeCode) continue;
          index.set(key, {
            topic: a.topic ?? null,
            learningOutcomeCode: a.learningOutcomeCode ?? null,
            learningOutcomeText: a.learningOutcomeText ?? null,
            pedagogicalDifficulty:
              typeof a.pedagogicalDifficulty === "number" ? a.pedagogicalDifficulty : null,
            difficultyConfidence: a.difficultyConfidence ?? null,
            skill: a.skill ?? null,
            questionType: a.questionType ?? null,
            analysisStatus: a.status ?? null,
          });
        } catch {
          // Skip malformed analysis lines
        }
      }
    } catch {
      // Skip unreadable analysis files
    }
  }
  return index;
}

function loadStudyQuestions(): StudyQuestion[] {
  const questions: StudyQuestion[] = [];
  const subjects = readdirSync(MANIFEST_BASE).filter((d) => {
    return existsSync(path.join(MANIFEST_BASE, d));
  });

  for (const subj of subjects) {
    const subjPath = path.join(MANIFEST_BASE, subj);
    // A subject may hold more than one source workbook (e.g. manifest.json +
    // manifest_mu2.json + manifest_tu2.json) — all of them are served.
    const manifestFiles = readdirSync(subjPath).filter((f) =>
      /^manifest.*\.json$/i.test(f)
    );
    const analysisIndex = loadAnalysisIndex(subjPath);

    for (const manifestFile of manifestFiles) {
      const manifestPath = path.join(subjPath, manifestFile);
      try {
        const manifest = JSON.parse(readFileSync(manifestPath, "utf-8"));
        for (const q of manifest.questions || []) {
          const qnum = q.q || q.questionNumber;
          if (!qnum) continue;
          // Never deliver unpublished questions or questions cancelled in the
          // official source (e.g. "13. İPTAL" in the exam key).
          if (q.published === false) continue;
          if (q.cancelledInSource) continue;

          // Manifests store `file` either as a bare filename or as a relative
          // path — always normalise to the bare filename.
          const originalFile = path.basename(
            q.file || `q-${String(qnum).padStart(2, "0")}.png`
          );
          const imagePath = `/study/${subj}-${originalFile}`;

          // Extract source book from filename (e.g., cal05, cal06, mu2, tu2)
          const mebiMatch = originalFile.match(/^mebi/i);
          const bookMatch = originalFile.match(/^((?:cal|nuli|mu|tu)\d+)/i);
          const sourceBook = mebiMatch
            ? "MEBI"
            : bookMatch
            ? bookMatch[1].toUpperCase()
            : "UNKNOWN";

          const analysis = analysisIndex.get(originalFile);
          questions.push({
            id:
              q.id ||
              // Question numbers restart per page, so the filename is the only
              // collision-free identifier within a subject.
              `STUDY-${subj.toUpperCase()}-${originalFile
                .replace(/\.png$/i, "")
                .toUpperCase()}`,
            subject: subj,
            sourceBook,
            questionNumber: qnum,
            page: q.page || 0,
            imagePath,
            answer: q.answer || null,
            unit: q.unit || null,
            unitName: q.unitName || null,
            section: q.section || null,
            questionText: q.questionText || null,
            topic: analysis?.topic ?? null,
            learningOutcomeCode: analysis?.learningOutcomeCode ?? null,
            learningOutcomeText: analysis?.learningOutcomeText ?? null,
            pedagogicalDifficulty: analysis?.pedagogicalDifficulty ?? null,
            difficultyConfidence: analysis?.difficultyConfidence ?? null,
            skill: analysis?.skill ?? null,
            questionType: analysis?.questionType ?? null,
            analysisStatus: analysis?.analysisStatus ?? null,
          });
        }
      } catch {
        // Skip malformed manifests
      }
    }
  }

  return questions;
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;
    const subject = searchParams.get("subject");
    const unit = searchParams.get("unit");
    const limit = parseInt(searchParams.get("limit") || "0", 10);
    const wrongMode = searchParams.get("wrong_mode");
    // Sıralama: unit asc, pedagogicalDifficulty asc (1=kolay, 2=orta, 3=zor)
    const sort = searchParams.get("sort") || "unit_difficulty";

    let questions = loadStudyQuestions();

    if (subject) {
      questions = questions.filter((q) => q.subject === subject);
    }
    if (unit) {
      questions = questions.filter((q) => q.unit === parseInt(unit, 10));
    }

    // Sıralama uygula
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

    // Never send answer keys to client unless in wrong_mode (repeat mode)
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

// Cevap kontrolü: doğru/yanlış söylenir, cevap anahtarı ASLA istemciye gitmez.
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
  if (typeof id !== "string" || id.length > 200 || typeof answer !== "string" || !/^[A-D]$/.test(answer)) {
    return NextResponse.json({ error: "id ve answer (A-D) alanları gerekli." }, { status: 400 });
  }
  try {
    const question = loadStudyQuestions().find((q) => q.id === id);
    if (!question || !question.answer) {
      return NextResponse.json({ error: "Soru bulunamadı." }, { status: 404, headers: { "Cache-Control": "no-store" } });
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
