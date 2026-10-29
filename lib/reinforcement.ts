/**
 * Pekiştirme Soruları Sistemi — AI'sız, kural tabanlı.
 *
 * Bu modül, günlük/haftalık/aylık değerlendirmelerden gelen yanlışları
 * analiz edip ünite başına 3+ yanlış eşiği geçenler için pekiştirme
 * görevleri oluşturur ve yönetir.
 */

import { loadAnswerRecords } from "./error-reason";
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
  /** Öğrenci cevapları */
  answers: Record<string, string | null>;
  /** Doğru/yanlış durumu */
  correctness: Record<string, boolean | null>;
  /** Görev durumu */
  status: TaskStatus;
  /** Son güncelleme tarihi */
  updatedAt: string;
}

/** Konu/ünite anahtarı oluşturur. */
function unitKey(q: { subject: string; unit: number | null; topic: string | null }): string {
  return `${q.subject}|${q.unit ?? "x"}|${q.topic ?? "-"}`.toLowerCase();
}

/** Assessment kaynağına göre kayıtları filtreler (şimdilik hepsini döndürür, ileride API'den gelecek). */
function getAssessmentRecords(source: AssessmentSource) {
  const all = loadAnswerRecords();
  // TODO: Gerçek implementasyonda source'a göre filtrelenecek (API'den gelecek)
  // Şimdilik tüm kayıtları döndür, kaynak ayrımı localStorage'ta yok
  return all;
}

/** Yanlış cevapları ünite/konu başına gruplayıp 3+ olanları tespit eder. */
export function detectWeakUnits(): Map<string, { count: number; subject: string; unit: number | null; unitName: string | null; topic: string; source: AssessmentSource }> {
  const weakUnits = new Map<string, { count: number; subject: string; unit: number | null; unitName: string | null; topic: string; source: AssessmentSource }>();
  
  // Tüm değerlendirme kaynaklarından kayıtları topla
  const allRecords = loadAnswerRecords();
  
  // Yanlış cevapları grupla
  const wrongByUnit = new Map<string, { count: number; subject: string; unit: number | null; unitName: string | null; topic: string; source: AssessmentSource }>();
  
  for (const record of allRecords) {
    if (!record.correct && record.topic) {
      const key = unitKey(record);
      const existing = wrongByUnit.get(key) || { count: 0, subject: record.subject, unit: record.unit, unitName: record.unitName, topic: record.topic, source: "gunluk" as AssessmentSource };
      existing.count++;
      wrongByUnit.set(key, existing);
    }
  }
  
  // 3+ yanlış olanları filtrele
  for (const [key, data] of wrongByUnit.entries()) {
    if (data.count >= 3) {
      weakUnits.set(key, data);
    }
  }
  
  return weakUnits;
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
  const weakUnits = detectWeakUnits();
  const existingTasks = loadReinforcementTasks();
  const now = new Date().toISOString();
  const updatedTasks = [...existingTasks];
  
  for (const [key, data] of weakUnits.entries()) {
    const existingIndex = updatedTasks.findIndex(t => t.id === key);
    
    if (existingIndex >= 0) {
      // Mevcut görevi güncelle
      const task = updatedTasks[existingIndex];
      task.wrongCount = data.count;
      task.source = data.source;
      task.updatedAt = now;
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
    tasks[index].questionIds = questionIds.slice(0, 5);
    // correctness ve answers başlat
    for (const qid of questionIds.slice(0, 5)) {
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