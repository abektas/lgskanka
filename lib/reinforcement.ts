/**
 * Pekiştirme Soruları Sistemi — AI'sız, kural tabanlı.
 *
 * Bu modül, günlük/haftalık/aylık değerlendirmelerden gelen yanlışları
 * analiz edip ünite başına 3+ yanlış eşiği geçenler için pekiştirme
 * görevleri oluşturur ve yönetir.
 */

import { loadAnswerRecords, type AnswerRecord } from "./error-reason";
import { subjects } from "../data/content";

/** Değerlendirme kaynağı. */
export type AssessmentSource = "gunluk" | "haftalik" | "aylik";

/** Pekiştirme görevi durumu. */
export type TaskStatus = "bekliyor" | "devam-ediyor" | "tamamlandi";

/** Pekiştirme görevi. */
export interface ReinforcementTask {
  /** Benzersiz görev ID'si: subject|unit|topic hash */
  id: string;
  subject: string;
  unit: number | null;
  unitName: string | null;
  topic: string;
  /** Hangi değerlendirme kaynağından geldi */
  source: AssessmentSource;
  /** Kaç yanlışla tetiklendi */
  wrongCount: number;
  /** Görev oluşturulma tarihi (ISO) */
  createdAt: string;
  /** 5 soruluk setin ID'leri */
  questionIds: string[];
  /** Daha önce sunulmuş soru ID'leri — tekrar aynı sorular atanmasın. */
  servedQuestionIds?: string[];
  /** Öğrenci cevapları */
  answers: Record<string, string | null>;
  /** Doğru/yanlış durumu */
  correctness: Record<string, boolean | null>;
  /** Görev durumu */
  status: TaskStatus;
  /** Son güncelleme tarihi */
  updatedAt: string;
}

/** Ünite anahtarı oluşturur — eşik ünite başına sayılır, konu başlığı başına değil. */
function unitKey(q: { subject: string; unit: number | null; unitName: string | null }): string {
  return `${q.subject}|${q.unit ?? q.unitName ?? "-"}`.toLowerCase();
}

/** Zayıf ders eşiği: doğruluk %60 altı ve en az 2 yanlış. */
export const WEAK_SUBJECT_ACCURACY = 0.6;
export const WEAK_SUBJECT_MIN_WRONG = 2;

/** Ders düzeyi (ünite bağımsız) zayıflık anahtarı. */
export function subjectWeakKey(subject: string): string {
  return `${subject.toLowerCase()}|__subject`;
}

/** Pekiştirme kayıtları tetikleyici değildir; yalnız değerlendirmeler sayılır. */
function isAssessmentRecord(record: AnswerRecord): boolean {
  return (record.source ?? "gunluk") !== "pekistirme";
}

/** En son değerlendirme günü (YYYY-MM-DD) ya da kayıt yoksa null. */
export function latestAssessmentDay(records: AnswerRecord[]): string | null {
  let latest: string | null = null;
  for (const record of records) {
    if (!isAssessmentRecord(record)) continue;
    const day = String(record.createdAt).slice(0, 10);
    if (!latest || day > latest) latest = day;
  }
  return latest;
}

export interface WeakUnit {
  count: number;
  subject: string;
  unit: number | null;
  unitName: string | null;
  topic: string;
  source: AssessmentSource;
}

/**
 * Yanlışlardan zayıf üniteleri ve zayıf dersleri türetir (saf fonksiyon).
 *
 * İki kural birlikte çalışır:
 * 1. Ünite kuralı — aynı ünitede 3+ yanlış.
 * 2. Ders kuralı — en son değerlendirme gününde dersin doğruluğu %60 altı ve
 *    en az 2 yanlış. Günlük çalışma her dersten 3–5 soru sorduğu için yanlışlar
 *    farklı ünitelere dağılır ve ünite kuralı hiç tetiklenmez; oysa öğrenci o
 *    derste zayıftır. Ders kuralı bu boşluğu kapatır ve görev, dersin o gün en
 *    çok yanlış yapılan ünitesinden soru seçer.
 */
export function computeWeakUnits(records: AnswerRecord[]): Map<string, WeakUnit> {
  const weakUnits = new Map<string, WeakUnit>();
  const assessments = records.filter(isAssessmentRecord);

  // --- Kural 1: ünite başına 3+ yanlış ---
  const wrongByUnit = new Map<string, { count: number; subject: string; unit: number | null; unitName: string | null; topic: string; source: AssessmentSource; topicCounts: Map<string, number> }>();

  for (const record of assessments) {
    if (record.correct) continue;
    // Ünite bilgisi olmadan kayıt bir üniteye bağlanamaz — uydurulmaz, atlanır.
    if (record.unit === null && !record.unitName) continue;
    const key = unitKey(record);
    const existing = wrongByUnit.get(key) || {
      count: 0,
      subject: record.subject,
      unit: record.unit,
      unitName: record.unitName,
      topic: record.topic ?? record.unitName ?? "Ünite tekrarı",
      source: "gunluk" as AssessmentSource,
      topicCounts: new Map<string, number>(),
    };
    existing.count++;
    if (record.topic) {
      existing.topicCounts.set(record.topic, (existing.topicCounts.get(record.topic) ?? 0) + 1);
    }
    wrongByUnit.set(key, existing);
  }

  for (const [key, data] of wrongByUnit.entries()) {
    if (data.count < 3) continue;
    // Görüntüleme etiketi: ünitede en sık yanlışlanan konu başlığı.
    let topic = data.topic;
    let best = -1;
    for (const [label, count] of data.topicCounts.entries()) {
      if (count > best) {
        best = count;
        topic = label;
      }
    }
    weakUnits.set(key, {
      count: data.count,
      subject: data.subject,
      unit: data.unit,
      unitName: data.unitName,
      topic,
      source: data.source,
    });
  }

  // --- Kural 2: en son değerlendirme gününde zayıf ders ---
  const latestDay = latestAssessmentDay(assessments);
  if (!latestDay) return weakUnits;

  const dayRecords = assessments.filter((r) => String(r.createdAt).slice(0, 10) === latestDay);
  const bySubject = new Map<string, AnswerRecord[]>();
  for (const record of dayRecords) {
    if (!record.subject) continue;
    const list = bySubject.get(record.subject) ?? [];
    list.push(record);
    bySubject.set(record.subject, list);
  }

  for (const [subject, list] of bySubject.entries()) {
    const wrong = list.filter((r) => !r.correct);
    if (wrong.length < WEAK_SUBJECT_MIN_WRONG) continue;
    const accuracy = (list.length - wrong.length) / list.length;
    if (accuracy >= WEAK_SUBJECT_ACCURACY) continue;
    // Aynı dersin ünite görevi varsa ikinci bir ders görevi açma.
    const hasUnitTask = [...weakUnits.values()].some((w) => w.subject === subject);
    if (hasUnitTask) continue;

    // Görev, dersin o gün en çok yanlış yapılan ünitesinden soru seçer.
    const unitWrongs = new Map<string, { unit: number | null; unitName: string | null; count: number; topic: string | null }>();
    for (const record of wrong) {
      if (record.unit === null && !record.unitName) continue;
      const key = unitKey(record);
      const item = unitWrongs.get(key) || {
        unit: record.unit,
        unitName: record.unitName,
        count: 0,
        topic: record.topic ?? null,
      };
      item.count++;
      if (record.topic) item.topic = record.topic;
      unitWrongs.set(key, item);
    }
    const weakest = [...unitWrongs.values()].sort((a, b) => b.count - a.count)[0];

    weakUnits.set(subjectWeakKey(subject), {
      count: wrong.length,
      subject,
      unit: weakest?.unit ?? null,
      unitName: weakest?.unitName ?? null,
      topic: weakest?.topic ?? weakest?.unitName ?? "Genel tekrar",
      source: "gunluk",
    });
  }

  return weakUnits;
}

/** Zayıf üniteleri tespit eder (yerel kayıtlardan). */
export function detectWeakUnits(): Map<string, WeakUnit> {
  return computeWeakUnits(loadAnswerRecords());
}

/**
 * Son `days` günün yanlışlarını ünite başına sayar — bir sonraki günün soru
 * seçiminde öncelik sırası olarak kullanılır (eşik yok).
 *
 * `excludeToday` (varsayılan açık): bugünün kayıtları planı değiştirmez, aksi
 * hâlde gün içinde verilen her yanlış sıralamayı kaydırır ve "kaldığın yerden
 * devam" indeksi başka sorulara denk gelir. Bugünün sonucu YARININ planını
 * belirler.
 */
export function weakUnitsForPlanning(
  records: AnswerRecord[] = loadAnswerRecords(),
  days = 3,
  excludeToday = true
): Array<{ subject: string; unit: number | null; unitName: string | null; count: number }> {
  const since = Date.now() - days * 24 * 60 * 60 * 1000;
  const today = new Date().toISOString().slice(0, 10);
  const grouped = new Map<string, { subject: string; unit: number | null; unitName: string | null; count: number }>();
  for (const record of records) {
    if (record.correct || !isAssessmentRecord(record)) continue;
    if (record.unit === null && !record.unitName) continue;
    if (new Date(record.createdAt).getTime() < since) continue;
    if (excludeToday && String(record.createdAt).slice(0, 10) >= today) continue;
    const key = unitKey(record);
    const item = grouped.get(key) || {
      subject: record.subject,
      unit: record.unit,
      unitName: record.unitName,
      count: 0,
    };
    item.count++;
    grouped.set(key, item);
  }
  return [...grouped.values()].sort((a, b) => b.count - a.count);
}

/** Mevcut pekiştirme görevlerini yükle. */
const TASK_STORAGE_KEY = "lgs_reinforcement_tasks";

export function loadReinforcementTasks(): ReinforcementTask[] {
  try {
    const raw = localStorage.getItem(TASK_STORAGE_KEY);
    const list = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

/** Pekiştirme görevlerini kaydet. */
function saveReinforcementTasks(tasks: ReinforcementTask[]): void {
  try {
    localStorage.setItem(TASK_STORAGE_KEY, JSON.stringify(tasks));
  } catch {
    // Depolama hatası sessizce atlanır
  }
}

/** Zayıf üniteler için pekiştirme görevleri oluştur/güncelle. */
export function syncReinforcementTasks(): ReinforcementTask[] {
  const records = loadAnswerRecords();
  const weakUnits = computeWeakUnits(records);
  const existingTasks = loadReinforcementTasks();
  const now = new Date().toISOString();
  const updatedTasks = [...existingTasks];

  // Görev anahtarı başına en yeni yanlışın zamanı — bitmiş görevi tazelemek için.
  const latestWrongByKey = new Map<string, { at: string; count: number }>();
  for (const [key, data] of weakUnits.entries()) {
    let latest = "";
    for (const record of records) {
      if (record.correct) continue;
      if ((record.source ?? "gunluk") === "pekistirme") continue;
      if (record.subject !== data.subject) continue;
      const matchesSubjectTask = key === subjectWeakKey(data.subject);
      if (!matchesSubjectTask) {
        if (record.unit === null && !record.unitName) continue;
        if (unitKey(record) !== key) continue;
      } else if (String(record.createdAt).slice(0, 10) !== latestAssessmentDay(records)) {
        // Ders görevi yalnız en son değerlendirme gününün yanlışlarıyla tazelenir.
        continue;
      }
      if (record.createdAt > latest) latest = record.createdAt;
    }
    latestWrongByKey.set(key, { at: latest, count: data.count });
  }

  for (const [key, data] of weakUnits.entries()) {
    const existingIndex = updatedTasks.findIndex((t) => t.id === key);
    const latestWrong = latestWrongByKey.get(key);

    if (existingIndex >= 0) {
      const task = updatedTasks[existingIndex];
      const previousUpdatedAt = task.updatedAt;
      task.wrongCount = data.count;
      task.source = data.source;
      task.updatedAt = now;
      if (
        task.status === "tamamlandi" &&
        latestWrong?.at &&
        latestWrong.at > previousUpdatedAt
      ) {
        // Görev bittikten sonra yeni yanlışlar geldi → taze soru setiyle yeniden aç.
        task.servedQuestionIds = [...(task.servedQuestionIds ?? []), ...task.questionIds];
        task.questionIds = [];
        task.answers = {};
        task.correctness = {};
        task.status = "bekliyor";
        task.createdAt = now;
      }
    } else {
      // Yeni görev oluştur - 5 soru seç (API'den gelecek, şimdilik placeholder)
      const newTask: ReinforcementTask = {
        id: key,
        subject: data.subject,
        unit: data.unit,
        unitName: data.unitName,
        topic: data.topic,
        source: data.source,
        wrongCount: data.count,
        createdAt: now,
        questionIds: [], // API'den 5 soru ID'si gelecek
        servedQuestionIds: [],
        answers: {},
        correctness: {},
        status: "bekliyor",
        updatedAt: now,
      };
      updatedTasks.push(newTask);
    }
  }

  // Artık zayıf olmayan görevleri "tamamlandi" yapma - sadece durumu koru
  // Kullanıcı tamamladığında manuel olarak güncellenecek

  saveReinforcementTasks(updatedTasks);
  return updatedTasks;
}

/** Görev durumu güncelle. */
export function updateTaskStatus(taskId: string, status: TaskStatus, answers?: Record<string, string>, correctness?: Record<string, boolean>): void {
  const tasks = loadReinforcementTasks();
  const index = tasks.findIndex(t => t.id === taskId);
  if (index >= 0) {
    tasks[index].status = status;
    tasks[index].updatedAt = new Date().toISOString();
    if (answers) tasks[index].answers = { ...tasks[index].answers, ...answers };
    if (correctness) tasks[index].correctness = { ...tasks[index].correctness, ...correctness };
    saveReinforcementTasks(tasks);
  }
}

/** Görev için 5 soru ID'si ata (API'den gelecek). */
export function assignQuestionsToTask(taskId: string, questionIds: string[]): void {
  const tasks = loadReinforcementTasks();
  const index = tasks.findIndex(t => t.id === taskId);
  if (index >= 0) {
    const chosen = questionIds.slice(0, 5);
    tasks[index].questionIds = chosen;
    // Sunulan sorular hatırlanır: görev tazelenirse aynı sorular tekrar atanmaz.
    tasks[index].servedQuestionIds = [
      ...new Set([...(tasks[index].servedQuestionIds ?? []), ...chosen]),
    ];
    // correctness ve answers başlat
    for (const qid of chosen) {
      tasks[index].answers[qid] = null;
      tasks[index].correctness[qid] = null;
    }
    tasks[index].updatedAt = new Date().toISOString();
    saveReinforcementTasks(tasks);
  }
}

/** Ders bazında görevleri getir. */
export function getTasksBySubject(subject: string): ReinforcementTask[] {
  const tasks = loadReinforcementTasks();
  return tasks.filter(t => t.subject === subject);
}

/** Tüm görevleri getir. */
export function getAllTasks(): ReinforcementTask[] {
  return loadReinforcementTasks();
}

/** Tamamlanmış görev sayısı. */
export function getCompletedTaskCount(): number {
  const tasks = loadReinforcementTasks();
  return tasks.filter(t => t.status === "tamamlandi").length;
}

/** Bekleyen görev sayısı. */
export function getPendingTaskCount(): number {
  const tasks = loadReinforcementTasks();
  return tasks.filter(t => t.status === "bekliyor").length;
}