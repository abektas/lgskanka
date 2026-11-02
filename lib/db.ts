/**
 * Sunucu tarafı Supabase (PostgREST) erişim yardımcıları.
 *
 * SADECE API route'ları tarafından kullanılabilir — secret key asla
 * istemciye gitmez. RLS secret key tarafından atlanır; anon anahtar
 * bu yapıda hiç kullanılmaz.
 */

const SUPABASE_URL = process.env.SUPABASE_URL || "https://mtucfiaiomyowkyeevvo.supabase.co";
const SUPABASE_SECRET = process.env.SUPABASE_SECRET_KEY || "";

function headers(extra: Record<string, string> = {}): Record<string, string> {
  return {
    apikey: SUPABASE_SECRET,
    Authorization: `Bearer ${SUPABASE_SECRET}`,
    "Content-Type": "application/json",
    ...extra,
  };
}

async function rest(path: string, init: RequestInit & { headers?: Record<string, string> } = {}) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    ...init,
    headers: headers(init.headers),
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Supabase ${res.status}: ${text.slice(0, 300)}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

/** Satır(lar) seç. Örn: select("students", "username=eq.ozge") */
export function dbSelect<T = unknown>(
  table: string,
  query: string,
  columns = "*"
): Promise<T[]> {
  return rest(`${table}?select=${encodeURIComponent(columns)}&${query}`) as Promise<T[]>;
}

/** Tek satır seç (yoksa null). */
export async function dbSelectOne<T = unknown>(
  table: string,
  query: string,
  columns = "*"
): Promise<T | null> {
  const rows = await dbSelect<T>(table, query + "&limit=1", columns);
  return rows[0] ?? null;
}

/** Satır ekle, eklenen satırı döndür. */
export function dbInsert<T = unknown>(
  table: string,
  row: Record<string, unknown> | Record<string, unknown>[]
): Promise<T[]> {
  return rest(table, {
    method: "POST",
    headers: { Prefer: "return=representation" },
    body: JSON.stringify(row),
  }) as Promise<T[]>;
}

/** Upsert (varsa güncelle, yoksa ekle). conflictColumns: unique sütunlar */
export function dbUpsert<T = unknown>(
  table: string,
  row: Record<string, unknown> | Record<string, unknown>[],
  conflictColumns: string
): Promise<T[]> {
  return rest(`${table}?on_conflict=${encodeURIComponent(conflictColumns)}`, {
    method: "POST",
    headers: {
      Prefer: "return=representation,resolution=merge-duplicates",
    },
    body: JSON.stringify(row),
  }) as Promise<T[]>;
}

/** Satır güncelle. Örn: dbUpdate("students", "id=eq.123", {name:"X"}) */
export function dbUpdate(
  table: string,
  query: string,
  patch: Record<string, unknown>
): Promise<null> {
  return rest(`${table}?${query}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  }) as Promise<null>;
}

/** Satır sil. */
export function dbDelete(table: string, query: string): Promise<null> {
  return rest(`${table}?${query}`, { method: "DELETE" }) as Promise<null>;
}

/** Öğrencinin seviye tespit (month 0) sınav sonucunu getirir. */
export async function getLevelTestResult(studentId: string) {
  return dbSelectOne(
    "exam_results",
    `student_id=eq.${studentId}&month=eq.0`,
    "by_subject,correct,wrong,empty,percentage,level,details"
  );
}

/** Kullanıcı adından öğrenci UUID'sini getirir. */
export async function getStudentIdByUsername(username: string): Promise<string | null> {
  const row = await dbSelectOne<{ id: string }>("students", `username=eq.${username}`, "id");
  return row?.id ?? null;
}

/** Tablodaki satır sayısını getirir (HEAD + Content-Range). */
export async function dbCount(table: string, query = ""): Promise<number> {
  const url = `${SUPABASE_URL}/rest/v1/${table}?select=id${query ? "&" + query : ""}`;
  const res = await fetch(url, {
    method: "HEAD",
    headers: { ...headers(), Prefer: "count=exact" },
    cache: "no-store",
  });
  const contentRange = res.headers.get("content-range") || "";
  const match = contentRange.match(/\/(\d+)$/);
  return match ? parseInt(match[1], 10) : 0;
}

/** Toplam öğrenci sayısını getirir. */
export async function getStudentCount(): Promise<number> {
  return dbCount("students");
}