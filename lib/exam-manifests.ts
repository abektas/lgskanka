/**
 * Sınav manifestleri — sunucu tarafı veri kaynağı.
 *
 * Bu modül manifest JSON'larını worker bundle'ına gömer; `fs` okuması
 * Cloudflare Workers'ta çalışmadığı için kullanılmaz. Manifestler cevap
 * anahtarı içerdiğinden SADECE API route'ları tarafından import edilir;
 * istemci bundle'ına asla dahil edilmez.
 */

import manifest00 from "../lgs_18_26/exams_by_month/00_seviye_tespit/manifest_00_seviye_tespit.json";
import manifest01 from "../lgs_18_26/exams_by_month/01_ay/manifest_01_ay.json";
import manifest02 from "../lgs_18_26/exams_by_month/02_ay/manifest_02_ay.json";
import manifest03 from "../lgs_18_26/exams_by_month/03_ay/manifest_03_ay.json";
import manifest04 from "../lgs_18_26/exams_by_month/04_ay/manifest_04_ay.json";
import manifest05 from "../lgs_18_26/exams_by_month/05_ay/manifest_05_ay.json";
import manifest06 from "../lgs_18_26/exams_by_month/06_ay/manifest_06_ay.json";
import manifest07 from "../lgs_18_26/exams_by_month/07_ay/manifest_07_ay.json";
import manifest08 from "../lgs_18_26/exams_by_month/08_ay/manifest_08_ay.json";
import manifest09 from "../lgs_18_26/exams_by_month/09_ay/manifest_09_ay.json";
import manifest10 from "../lgs_18_26/exams_by_month/10_ay/manifest_10_ay.json";
import manifest11 from "../lgs_18_26/exams_by_month/11_ay/manifest_11_ay.json";

export interface ExamQuestion {
  id: string;
  month: number;
  monthName: string;
  subject: string;
  questionNumber: number;
  file: string;
  answer: string | null;
  examYear: number;
  originalYear: number;
  difficultyScore: number;
  questionType: string | null;
  visualDependency: string | null;
  underlineDependent: boolean | null;
  topic: string | null;
  unit: number | null;
  unitName: string | null;
  topicConfidence?: number;
  topicProbs?: Record<string, number>;
}

export interface ExamManifest {
  month: number;
  monthName: string;
  totalQuestions: number;
  durationMinutes: number;
  subjectDurations?: Record<string, number>;
  questions: ExamQuestion[];
}

const manifests: ExamManifest[] = [
  manifest00,
  manifest01,
  manifest02,
  manifest03,
  manifest04,
  manifest05,
  manifest06,
  manifest07,
  manifest08,
  manifest09,
  manifest10,
  manifest11,
] as unknown as ExamManifest[];

/** Ay numarasından manifest getirir (0 = seviye tespit). */
export function getExamManifest(month: number): ExamManifest | null {
  return manifests.find((m) => m.month === month) ?? null;
}

/** Mevcut sınav aylarının listesi (liste API'si için). */
export function listExamMonths(): Array<{
  month: number;
  monthName: string;
  name: string;
  totalQuestions: number;
  durationMinutes: number;
}> {
  return manifests.map((m) => ({
    month: m.month,
    monthName: m.monthName,
    name: m.monthName,
    totalQuestions: m.totalQuestions,
    durationMinutes: m.durationMinutes,
  }));
}

/**
 * İstemciye gönderilecek soru görünümü: cevap anahtarı ÇIKARILIR,
 * görsel yolu /exams/ altından hesaplanır.
 */
export function toPublicQuestion(
  q: ExamQuestion,
  monthName: string
): Omit<ExamQuestion, "answer"> & { imagePath: string } {
  const { answer, ...rest } = q;
  return {
    ...rest,
    monthName,
    imagePath: `/exams/${monthName}/${q.subject}/${q.file}`,
  };
}