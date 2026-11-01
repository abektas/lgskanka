/**
 * Online veri senkron köprüsü.
 *
 * Öğrenci verileri (cevap kayıtları, çalışma durumu, pekiştirme görevleri)
 * Supabase'de tutulur. Tarayıcıdaki localStorage yalnızca hızlı görüntüleme
 * için "ayna" olarak kullanılır; gerçek veri her zaman sunucudur.
 */

const TOKEN_KEY = "lgs_token";

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* depolama kapalıysa yok say */
  }
}

export function clearAuthToken(): void {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* yok say */
  }
}

/** Authorization başlıklı fetch. */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init.headers as Record<string, string>) || {}),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  return fetch(path, { ...init, headers });
}

/** Cevap kaydını sunucuya gönder (ateşle-unut). */
export function pushAnswerRecord(record: {
  questionId: string;
  subject: string;
  unit: number | null;
  unitName: string | null;
  topic: string | null;
  selectedAnswer: string;
  correct: boolean;
  errorReasonCode: string | null;
  timeSpentSec: number;
  source?: string;
  createdAt: string;
}): void {
  if (!getAuthToken()) return;
  apiFetch("/api/answer-records", {
    method: "POST",
    body: JSON.stringify({ records: [record] }),
  }).catch(() => {});
}

/** Sunucudaki cevap kayıtlarını getir (ayna için). */
export async function pullAnswerRecords(): Promise<Array<Record<string, unknown>>> {
  if (!getAuthToken()) return [];
  try {
    const res = await apiFetch("/api/answer-records?limit=1000");
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

/** Günlük çalışma durumunu kaydet (kaldığın yerden devam et). */
export function pushStudySession(data: {
  solved: number;
  correct: number;
  target: number;
  state?: Record<string, unknown>;
  date?: string;
}): void {
  if (!getAuthToken()) return;
  apiFetch("/api/study-session", {
    method: "POST",
    body: JSON.stringify(data),
  }).catch(() => {});
}

/** Pekiştirme görevlerini sunucuya gönder. */
export function pushReinforcementTasks(tasks: object[]): void {
  if (!getAuthToken() || tasks.length === 0) return;
  apiFetch("/api/reinforcement-tasks", {
    method: "POST",
    body: JSON.stringify({ tasks }),
  }).catch(() => {});
}

/** Sunucudaki pekiştirme görevlerini getir. */
export async function pullReinforcementTasks(): Promise<Array<Record<string, unknown>>> {
  if (!getAuthToken()) return [];
  try {
    const res = await apiFetch("/api/reinforcement-tasks");
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

/** Deneme oturumu kaydet (yarım kalmış sınav). */
export function pushExamSession(month: number, answers: Record<string, string>, currentIndex: number): void {
  if (!getAuthToken()) return;
  apiFetch("/api/exams-session", {
    method: "POST",
    body: JSON.stringify({ month, answers, currentIndex }),
  }).catch(() => {});
}

/** Yarım kalmış deneme oturumunu getir. */
export async function pullExamSession(month: number): Promise<{
  answers: Record<string, string>;
  current_index: number;
} | null> {
  if (!getAuthToken()) return null;
  try {
    const res = await apiFetch(`/api/exams-session?month=${month}`);
    if (!res.ok) return null;
    const data = await res.json();
    return data.session ?? null;
  } catch {
    return null;
  }
}