import { NextRequest, NextResponse } from "next/server";
import { createHash, timingSafeEqual } from "node:crypto";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { getStudentIdByUsername, getLevelTestResult, dbSelect } from "../../../lib/db";
import { authFromRequest } from "../../../lib/auth";
import { rateLimit, getClientIp } from "../../../lib/rate-limit";

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

// Per-subject önceden işlenmiş manifestolar — CPU limitini aşmamak için
// her istekte tüm sorular yerine yalnızca ilgili ders dosyası yüklenir.
const SUBJECT_FILES: Record<string, string> = {
  turkce: "study_manifests/questions_turkce.json",
  matematik: "study_manifests/questions_matematik.json",
  fen: "study_manifests/questions_fen.json",
  "inkilap-tarihi": "study_manifests/questions_inkilap-tarihi.json",
  "din-kulturu": "study_manifests/questions_din-kulturu.json",
  ingilizce: "study_manifests/questions_ingilizce.json",
};

// Promise tabanlı önbellek — eşzamanlı isteklerde tekrar yüklemeyi önler
const subjectCache = new Map<string, Promise<StudyQuestion[]>>();

async function loadSubjectQuestions(subject: string): Promise<StudyQuestion[]> {
  const cached = subjectCache.get(subject);
  if (cached) return cached;

  const promise = (async () => {
    const file = SUBJECT_FILES[subject];
    if (!file) return [];

    const data = await fetchJson(file);
    const questions: StudyQuestion[] = [];

    for (const q of data.questions || []) {
      questions.push({
        id: q.id || `STUDY-${subject.toUpperCase()}-${String(q.questionNumber || 0)}`,
        subject: q.subject || subject,
        sourceBook: q.sourceBook || "UNKNOWN",
        questionNumber: q.questionNumber || 0,
        page: q.page || 0,
        imagePath: q.imagePath || null,
        answer: q.answer || null,
        unit: q.unit ?? null,
        unitName: q.unitName ?? null,
        section: q.section ?? null,
        questionText: q.questionText ?? null,
        topic: q.topic ?? null,
        learningOutcomeCode: q.learningOutcomeCode ?? null,
        learningOutcomeText: q.learningOutcomeText ?? null,
        pedagogicalDifficulty: q.pedagogicalDifficulty ?? null,
        difficultyConfidence: q.difficultyConfidence ?? null,
        skill: q.skill ?? null,
        questionType: q.questionType ?? null,
        analysisStatus: q.analysisStatus ?? null,
      });
    }
    return questions;
  })();

  subjectCache.set(subject, promise);
  return promise;
}

async function loadAllQuestions(): Promise<StudyQuestion[]> {
  const subjects = Object.keys(SUBJECT_FILES);
  const batches = await Promise.all(subjects.map((s) => loadSubjectQuestions(s)));
  return batches.flat();
}

let allQuestionsPromise: Promise<StudyQuestion[]> | null = null;

export async function getQuestions(): Promise<StudyQuestion[]> {
  if (!allQuestionsPromise) {
    allQuestionsPromise = loadAllQuestions();
  }
  return allQuestionsPromise;
}

// Yalnızca tek ders yükleyen hızlı yol — CPU tasarrufu
async function getQuestionsForSubject(subject: string): Promise<StudyQuestion[]> {
  return loadSubjectQuestions(subject);
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;
    const subject = searchParams.get("subject");
    const unit = searchParams.get("unit");
    const limit = parseInt(searchParams.get("limit") || "0", 10);
    const sort = searchParams.get("sort") || "unit_difficulty";
    const fresh = searchParams.get("fresh") === "1"; // günlük çalışma: son 30 günde çözülenler dışlanır
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

    // Ders belirtilmişse yalnızca o dersin dosyasını yükle (CPU tasarrufu)
    let questions = subject
      ? await getQuestionsForSubject(subject)
      : await getQuestions();

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

    if (limit > 0 && fresh) {
      // Günlük çalışma rotasyonu: son 30 günde çözülen sorular dışlanır ki
      // her gün yeni sorular gelsin (havuz tükenirse çözülenler geri döner).
      const auth = await authFromRequest(request);
      if (auth) {
        try {
          const since = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
          const rows = await dbSelect<{ question_id: string }>(
            "answer_records",
            `student_id=eq.${encodeURIComponent(auth.sub)}&created_at=gte.${since}&limit=2000`,
            "question_id"
          );
          const answered = new Set(rows.map((r) => r.question_id));
          if (answered.size > 0) {
            questions = [
              ...questions.filter((q) => !answered.has(q.id)),
              ...questions.filter((q) => answered.has(q.id)),
            ];
          }
        } catch {
          // Sunucu kaydı okunamazsa rotasyonsuz devam et.
        }
      }
    }

    if (limit > 0) {
      questions = questions.slice(0, limit);
    }

    const publicQuestions = questions.map((q) => {
      const { answer: _answerKey, ...rest } = q;
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
  const auth = await authFromRequest(request);
  if (!auth) return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });
  const limit = rateLimit(`study-answer:${auth.sub}:${getClientIp(request)}`, 120, 60_000);
  if (!limit.allowed) {
    return NextResponse.json({ error: "Çok sık cevap kontrolü yapıldı. Bir dakika sonra tekrar dene." }, { status: 429 });
  }

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