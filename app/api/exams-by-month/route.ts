import { NextRequest, NextResponse } from "next/server";
import { readdirSync, readFileSync, existsSync, statSync } from "fs";
import path from "path";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const EXAMS_BASE = path.join(process.cwd(), "lgs_18_26", "exams_by_month");

interface ExamQuestion {
  id: string;
  month: number;
  monthName: string;
  subject: string;
  questionNumber: number;
  imagePath: string;
  answer: string | null;
  file: string;
  originalYear: number;
  difficultyScore: number;
  questionType: string | null;
  visualDependency: string | null;
  underlineDependent: boolean | null;
  topic: string | null;
  unit: number | null;
  unitName: string | null;
}

interface ExamManifest {
  month: number;
  monthName: string;
  totalQuestions: number;
  durationMinutes: number;
  questions: ExamQuestion[];
}

function loadExamManifest(month: number): ExamManifest | null {
  const monthName = month === 0 ? "00_seviye_tespit" : `${month.toString().padStart(2, "0")}_ay`;
  const manifestPath = path.join(EXAMS_BASE, monthName, `manifest_${monthName}.json`);
  
  if (!existsSync(manifestPath)) {
    return null;
  }
  
  try {
    return JSON.parse(readFileSync(manifestPath, "utf-8"));
  } catch {
    return null;
  }
}

function listAvailableMonths(): number[] {
  if (!existsSync(EXAMS_BASE)) return [];
  
  const entries = readdirSync(EXAMS_BASE);
  const months: number[] = [];
  
  for (const entry of entries) {
    const fullPath = path.join(EXAMS_BASE, entry);
    if (!statSync(fullPath).isDirectory()) continue;
    
    const match = entry.match(/^(\d{2})_ay$/) || entry.match(/^00_seviye_tespit$/);
    if (match) {
      const month = entry === "00_seviye_tespit" ? 0 : parseInt(match[1], 10);
      months.push(month);
    }
  }
  
  return months.sort((a, b) => a - b);
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;
    const monthParam = searchParams.get("month");
    const subject = searchParams.get("subject");
    const listOnly = searchParams.get("list") === "true";

    // Sadece mevcut ayları listele
    if (listOnly) {
      const months = listAvailableMonths();
      const monthInfos = months.map(m => {
        const manifest = loadExamManifest(m);
        return {
          month: m,
          name: manifest?.monthName || (m === 0 ? "00_seviye_tespit" : `${m.toString().padStart(2, "0")}_ay`),
          totalQuestions: manifest?.totalQuestions || 0,
          durationMinutes: manifest?.durationMinutes || 180,
        };
      });
      return NextResponse.json({ months: monthInfos });
    }

    // Belirli bir ay
    if (!monthParam) {
      return NextResponse.json(
        { error: "month parametresi gerekli" },
        { status: 400 }
      );
    }

    const month = parseInt(monthParam, 10);
    if (isNaN(month) || month < 0 || month > 11) {
      return NextResponse.json(
        { error: "Geçersiz ay (0-11)" },
        { status: 400 }
      );
    }

    const manifest = loadExamManifest(month);
    if (!manifest) {
      return NextResponse.json(
        { error: "Bu ay için sınav bulunamadı" },
        { status: 404 }
      );
    }

    let questions = manifest.questions;

    if (subject) {
      questions = questions.filter((q) => q.subject === subject);
    }

    // Cevap anahtarı asla istemciye gitmez; imagePath'i public/exams/ altından yapılandır
    const publicQuestions = questions.map((q) => {
      const { answer, ...rest } = q;
      return {
        ...rest,
        imagePath: `/exams/${manifest.monthName}/${q.subject}/${q.file}`,
      };
    });

    return NextResponse.json(
      {
        month: manifest.month,
        monthName: manifest.monthName,
        durationMinutes: manifest.durationMinutes,
        totalQuestions: publicQuestions.length,
        items: publicQuestions,
      },
      { headers: { "Cache-Control": "no-store" } }
    );
  } catch {
    return NextResponse.json(
      { error: "Sınav verisi şu anda kullanılamıyor." },
      { status: 503, headers: { "Cache-Control": "no-store" } }
    );
  }
}