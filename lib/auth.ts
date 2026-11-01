/**
 * Sunucu tarafı kimlik doğrulama: şifre hash + JWT oturum token'ı.
 *
 * - Şifreler PBKDF2-SHA256 ile hash'lenir, düz metin asla saklanmaz.
 * - JWT HMAC-SHA256 ile imzalanır; AUTH_JWT_SECRET ile imzalanır.
 * - Web Crypto kullanır (Cloudflare Workers + Node 18+ uyumlu).
 *
 * Not: PBKDF2 iterasyon sayısı Workers ücretsiz planın CPU limitine
 * uygun seçildi (10k). Ücretli plana geçilirse 200k'ya çıkarılabilir.
 */

const PBKDF2_ITERATIONS = 10_000;

function getJwtSecret(): string {
  const secret = process.env.AUTH_JWT_SECRET;
  if (!secret) throw new Error("AUTH_JWT_SECRET tanımlı değil");
  return secret;
}

const enc = new TextEncoder();

function toHex(buf: ArrayBuffer): string {
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function fromHex(hex: string): Uint8Array {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

function timingSafeEqualStr(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}

/** Şifreyi hash'le: "pbkdf2$iter$saltHex$hashHex" formatında döner. */
export async function hashPassword(password: string): Promise<string> {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(password),
    "PBKDF2",
    false,
    ["deriveBits"]
  );
  const bits = await crypto.subtle.deriveBits(
    {
      name: "PBKDF2",
      hash: "SHA-256",
      salt: salt as BufferSource,
      iterations: PBKDF2_ITERATIONS,
    },
    key,
    256
  );
  return `pbkdf2$${PBKDF2_ITERATIONS}$${toHex(salt.buffer)}$${toHex(bits)}`;
}

/** Şifreyi doğrula. */
export async function verifyPassword(password: string, stored: string): Promise<boolean> {
  const parts = stored.split("$");
  if (parts.length !== 4 || parts[0] !== "pbkdf2") return false;
  const iterations = parseInt(parts[1], 10);
  const salt = fromHex(parts[2]);
  const expected = parts[3];
  if (!iterations || !salt.length || !expected) return false;

  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(password),
    "PBKDF2",
    false,
    ["deriveBits"]
  );
  const bits = await crypto.subtle.deriveBits(
    {
      name: "PBKDF2",
      hash: "SHA-256",
      salt: salt as BufferSource,
      iterations,
    },
    key,
    256
  );
  return timingSafeEqualStr(toHex(bits), expected);
}

export interface JwtPayload {
  sub: string; // student id
  username: string;
  name: string;
  exp: number; // epoch saniye
}

function b64url(data: ArrayBuffer | string): string {
  const bytes = typeof data === "string" ? enc.encode(data) : new Uint8Array(data);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/** JWT imzala (30 gün geçerli). */
export async function signToken(payload: Omit<JwtPayload, "exp">): Promise<string> {
  const exp = Math.floor(Date.now() / 1000) + 30 * 24 * 60 * 60;
  const header = b64url(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = b64url(JSON.stringify({ ...payload, exp }));
  const data = `${header}.${body}`;
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(getJwtSecret()),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(data));
  return `${data}.${b64url(sig)}`;
}

/** JWT doğrula; geçersizse null döner. */
export async function verifyToken(token: string): Promise<JwtPayload | null> {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const data = `${parts[0]}.${parts[1]}`;
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(getJwtSecret()),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["verify"]
  );
  let sig: Uint8Array;
  try {
    sig = fromHex(b64urlToHex(parts[2]));
  } catch {
    return null;
  }
  const valid = await crypto.subtle.verify(
    "HMAC",
    key,
    sig as BufferSource,
    enc.encode(data)
  );
  if (!valid) return null;
  try {
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    if (typeof payload.exp === "number" && payload.exp < Date.now() / 1000) return null;
    return payload as JwtPayload;
  } catch {
    return null;
  }
}

function b64urlToHex(b64url: string): string {
  const b64 = b64url.replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(b64 + "===".slice((b64.length + 3) % 4));
  let hex = "";
  for (let i = 0; i < bin.length; i++) {
    hex += bin.charCodeAt(i).toString(16).padStart(2, "0");
  }
  return hex;
}

/** İstekten Authorization başlığındaki token'ı çöz. */
export async function authFromRequest(
  request: Request
): Promise<JwtPayload | null> {
  const header = request.headers.get("Authorization") || "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : null;
  if (!token) return null;
  return verifyToken(token);
}

/**
 * Kullanıcı adını normalize et.
 * "Ali @lgsdeneme1", "@lgsdeneme1", " LgsDeneme1 " gibi girişleri
 * "lgsdeneme1" biçimine indirger.
 */
export function normalizeUsername(raw: unknown): string {
  let u = String(raw ?? "")
    .trim()
    .toLocaleLowerCase("tr-TR")
    .replace(/\s+/g, "");
  const at = u.lastIndexOf("@");
  if (at >= 0) u = u.slice(at + 1);
  return u;
}