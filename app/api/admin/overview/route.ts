import { NextRequest, NextResponse } from "next/server";
import { dbSelect, dbSelectOne, dbUpdate, dbDelete } from "../../../../lib/db";
import { isAdminRequest, ADMIN_UNAUTHORIZED } from "../../../../lib/admin";
import { getExamManifest } from "../../../../lib/exam-manifests";
import { normalizeUsername, hashPassword } from "../../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type OverviewRow = {
  id: string;
  username: string;
  name: string;
  gender: string;
  variant: number;
  registered_at: string;
  total_answered: number;
  total_correct: number;
  last_activity: string | null;
  exam_count: number;
  last_exam_month: number | null;
  last_exam_percentage: number | null;
  last_exam_level: string | null;
  open_tasks: number;
};

type ExamSessionRow = {
  student_id: string;
  month: number;
  answers: Record<string, unknown>;
  current_index: number;
  updated_at: string;
};

type StudySessionRow = {
  student_id: string;
  session_date: string;
  solved: number;
  correct: number;
  target: number;
};

function examLabel(month: number): string {
  return month === 0 ? "Seviye Tespit" : month + ". Ay Denemesi";
}

/**
 * GET /api/admin/overview — tüm öğrencilerin özet ilerlemesi (öğretmen).
 * GET /api/admin/overview?id=<uuid> — tek öğrencinin detayı.
 */
export async function GET(req: NextRequest) {
  if (!isAdminRequest(req)) {
    return NextResponse.json(ADMIN_UNAUTHORIZED, { status: 401 });
  }

  const id = req.nextUrl.searchParams.get("id");
  if (id) {
    // Öğrenci detayı: cevaplar + denemeler + pekiştirme + devam eden oturumlar
    const [records, exams, tasks, examSessions, studySessions] = await Promise.all([
      dbSelect<{
        question_id: string;
        subject: string;
        unit_name: string | null;
        topic: string | null;
        correct: boolean;
        error_reason_code: string | null;
        created_at: string;
      }>(
        "answer_records",
        `student_id=eq.${encodeURIComponent(id)}&order=created_at.desc&limit=300`
      ),
      dbSelect<{
        month: number;
        month_name: string;
        correct: number;
        wrong: number;
        empty: number;
        percentage: number;
        level: string;
        completed_at: string;
      }>("exam_results", `student_id=eq.${encodeURIComponent(id)}&order=completed_at.desc`),
      dbSelect<{
        id: string;
        subject: string;
        unit_name: string | null;
        topic: string | null;
        status: string;
        wrong_count: number;
      }>("reinforcement_tasks", `student_id=eq.${encodeURIComponent(id)}&order=created_at.desc`),
      dbSelect<ExamSessionRow>(
        "exam_sessions",
        `student_id=eq.${encodeURIComponent(id)}&order=updated_at.desc`
      ),
      dbSelect<StudySessionRow>(
        "study_sessions",
        `student_id=eq.${encodeURIComponent(id)}&order=session_date.desc&limit=30`
      ),
    ]);

    // Yanlış yapılan konu dağılımı (son 300 cevap)
    const wrongByUnit = new Map<string, number>();
    for (const r of records) {
      if (r.correct) continue;
      const label = r.unit_name
        ? `${r.subject} / ${r.unit_name}${r.topic ? " / " + r.topic : ""}`
        : r.subject;
      wrongByUnit.set(label, (wrongByUnit.get(label) || 0) + 1);
    }
    const weakTopics = [...wrongByUnit.entries()]
      .map(([label, count]) => ({ label, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 15);

    return NextResponse.json({
      studentId: id,
      totalAnswered: records.length,
      totalCorrect: records.filter((r) => r.correct).length,
      weakTopics,
      exams,
      tasks,
      examSessions: examSessions.map((e) => ({
        month: e.month,
        label: examLabel(e.month),
        answered: Object.values(e.answers || {}).filter(Boolean).length,
        total: getExamManifest(e.month)?.totalQuestions ?? 90,
        currentIndex: e.current_index,
        updatedAt: e.updated_at,
      })),
      studySessions,
      recent: records.slice(0, 20),
    });
  }

  // Tüm öğrencilerin özeti
  const [students, examSessions, studySessions] = await Promise.all([
    dbSelect<OverviewRow>("student_overview", "order=last_activity.desc.nullslast"),
    dbSelect<ExamSessionRow>("exam_sessions", "order=updated_at.desc"),
    dbSelect<StudySessionRow>("study_sessions", "order=session_date.desc&limit=300"),
  ]);

  const today = new Date().toISOString().slice(0, 10);
  const merged = students.map((s) => {
    const activeExams = examSessions
      .filter((e) => e.student_id === s.id)
      .map((e) => ({
        month: e.month,
        label: examLabel(e.month),
        answered: Object.values(e.answers || {}).filter(Boolean).length,
        total: getExamManifest(e.month)?.totalQuestions ?? 90,
        updatedAt: e.updated_at,
      }));
    const todayRow = studySessions.find(
      (r) => r.student_id === s.id && r.session_date === today
    );
    return {
      ...s,
      active_exams: activeExams,
      today_solved: todayRow?.solved ?? 0,
      today_correct: todayRow?.correct ?? 0,
      today_target: todayRow?.target ?? 24,
    };
  });

  return NextResponse.json({ students: merged });
}

/**
 * POST /api/admin/reset-password — öğretmen bir öğrencinin şifresini sıfırlar.
 * { username, newPassword }
 */
export async function POST(req: NextRequest) {
  if (!isAdminRequest(req)) {
    return NextResponse.json(ADMIN_UNAUTHORIZED, { status: 401 });
  }

  const body = await req.json().catch(() => null);
  const username = normalizeUsername(body?.username);
  const newPassword = String(body?.newPassword || "");

  if (newPassword.length < 4) {
    return NextResponse.json(
      { error: "Yeni şifre en az 4 karakter olmalı." },
      { status: 400 }
    );
  }

  const student = await dbSelectOne<{ id: string }>(
    "students",
    `username=eq.${encodeURIComponent(username)}`
  );
  if (!student) {
    return NextResponse.json({ error: "Öğrenci bulunamadı." }, { status: 404 });
  }

  // PBKDF2 hash üret (lib/auth ile aynı algoritma)
  const password_hash = await hashPassword(newPassword);
  await dbUpdate("students", `id=eq.${encodeURIComponent(student.id)}`, {
    password_hash,
  });

  return NextResponse.json({ success: true, username });
}

/**
 * DELETE /api/admin/overview — seçilen öğrencileri sil.
 * { ids: ["uuid", ...] } — tüm ilgili kayıtlar (cevaplar, denemeler, vb.)
 * FK on-delete cascade ile birlikte silinir.
 */
export async function DELETE(req: NextRequest) {
  if (!isAdminRequest(req)) {
    return NextResponse.json(ADMIN_UNAUTHORIZED, { status: 401 });
  }

  const body = await req.json().catch(() => null);
  const ids: string[] = Array.isArray(body?.ids) ? body.ids.map(String) : [];
  const valid = ids.filter((id) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id));

  if (valid.length === 0) {
    return NextResponse.json({ error: "Geçerli öğrenci id'si gerekli." }, { status: 400 });
  }
  if (valid.length > 50) {
    return NextResponse.json({ error: "Tek seferde en fazla 50 öğrenci silinebilir." }, { status: 400 });
  }

  try {
    for (const id of valid) {
      await dbDelete("students", `id=eq.${encodeURIComponent(id)}`);
    }
    return NextResponse.json({ success: true, deleted: valid.length });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 500 });
  }
}