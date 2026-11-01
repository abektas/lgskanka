import { NextRequest, NextResponse } from "next/server";
import { createHash, timingSafeEqual } from "node:crypto";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { getStudentIdByUsername, getLevelTestResult } from "../../../lib/db";

// Görseller /r2 proxy rotasından sunulur (yalnızca .webp).
const R2_PUBLIC_URL = "https://lgskanka.alibey.workers.dev/r2";

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

// Manifestolar sunucu tarafında R2 binding'den okunur; cevap anahtarı
// içerdiğinden herkese açık URL'den asla çekilmez.
async function fetchJson(key: string): Promise<any> {
  const { env } = await getCloudflareContext();
  const bucket = (
    env as unknown as {
      R2: { get(key: string): Promise<{ json(): Promise<unknown> } | null> };
    }
  ).R2;
  const object = await bucket.get(key);
  if (!object) throw new Error(`R2 object missing: ${key}`);
  return object.json();
}

async function loadImageMap(): Promise<Map<string, string>> {
  const raw = await fetchJson("study_manifests/image_map.json");
  const result = new Map<string, string>();
  for (const [localPath, info] of Object.entries(raw as Record<string, any>)) {
    const name = localPath.split("/").pop();
    const webpPath = info?.webp_path;
    if (name && webpPath) {
      const r2Key = webpPath.split("/webp/")[1] || "";
      result.set(name, r2Key);
    }
  }
  return result;
}

async function loadAllQuestions(): Promise<StudyQuestion[]> {
  const imageMap = await loadImageMap();
  const data = await fetchJson("study_manifests/all_questions.json");
  const questions: StudyQuestion[] = [];

  for (const q of data.questions || []) {
    if (q.published === false) continue;
    if (q.cancelledInSource) continue;

    const originalFile = q.file || `q-${q.q || 0}.png`;
    let qnum = q.q || q.questionNumber;
    if (!qnum) {
      const numMatch = originalFile.match(/(\d+)\.png$/i);
      qnum = numMatch ? parseInt(numMatch[1], 10) : 1;
    }
    // Try exact match first, then basename match
    let webpPath = imageMap.get(originalFile);
    if (!webpPath) {
      const basename = originalFile.split("/").pop();
      webpPath = imageMap.get(basename);
    }
    const imagePath = webpPath ? `${R2_PUBLIC_URL}/${webpPath}` : null;

    const mebiMatch = originalFile.match(/^mebi/i);
    const bookMatch = originalFile.match(/^((?:cal|nuli|mu|tu)\d+)/i);
    const sourceBook = mebiMatch ? "MEBI" : bookMatch ? bookMatch[1].toUpperCase() : "UNKNOWN";

    questions.push({
      id:
        q.id ||
        `STUDY-${(q._subject || "UNKNOWN").toUpperCase()}-${originalFile
          .replace(/\.png$/i, "")
          .toUpperCase()}`,
      subject: q._subject || "UNKNOWN",
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
  return questions;
}

let questionsCache: StudyQuestion[] | null = null;

async function getQuestions(): Promise<StudyQuestion[]> {
  if (questionsCache) return questionsCache;
  questionsCache = await loadAllQuestions();
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
    const profileId = searchParams.get("profileId"); // Kişiselleştirme için öğrenci kullanıcı adı

    // Kişiselleştirilmiş ders kotalarını hesapla
    let subjectLimits: Record<string, number> = {
      turkce: 5,
      matematik: 5,
      fen: 5,
      "inkilap-tarihi": 3,
      "din-kulturu": 3,
      ingilizce: 3,
    };

    if (profileId) {
      const studentId = await getStudentIdByUsername(profileId);
      if (studentId) {
        const levelTest = await getLevelTestResult(studentId);
        if (levelTest && typeof levelTest === "object" && "by_subject" in levelTest) {
          // Her dersin yüzdesini hesapla; %60 altı zayıf sayılır
          const bySubject = (levelTest as any).by_subject as Record<string, { correct: number; total: number }>;
          const weakSubjects = new Set<string>();
          for (const [subject, stats] of Object.entries(bySubject)) {
            if (stats.total > 0 && (stats.correct / stats.total) < 0.6) {
              weakSubjects.add(subject);
            }
          }
          // Zayıf derslere +2 soru, güçlü derslerden -1 (toplam 24 korunur)
          let totalAdjustment = 0;
          for (const subject of Object.keys(subjectLimits)) {
            if (weakSubjects.has(subject)) {
              subjectLimits[subject] += 2;
              totalAdjustment += 2;
            }
          }
          // Toplam 24'e inmesi için güçlü derslerden azalt
          const strongSubjects = Object.keys(subjectLimits).filter((s) => !weakSubjects.has(s) && subjectLimits[s] > 1);
          for (const subject of strongSubjects) {
            if (totalAdjustment <= 0) break;
            subjectLimits[subject] -= 1;
            totalAdjustment -= 1;
          }
        }
      }
    }

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
  } catch (e) {
    return NextResponse.json(
      { error: "Çalışma verisi şu anda kullanılamıyor.", detail: String(e) },
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
    const correct = timingSafeEqual(submitted, expected);

    // Return question metadata so client can save answer record with full context
    return NextResponse.json(
      {
        correct,
        question: {
          id: question.id,
          subject: question.subject,
          unit: question.unit,
          unitName: question.unitName,
          topic: question.topic,
        },
      },
      { headers: { "Cache-Control": "no-store" } }
    );
  } catch (e) {
    return NextResponse.json(
      { error: "Cevap kontrolü şu anda kullanılamıyor.", detail: String(e) },
      { status: 503, headers: { "Cache-Control": "no-store" } }
    );
  }
}