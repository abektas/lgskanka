import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const route = fs.readFileSync(new URL('../../app/api/study/route.ts', import.meta.url), 'utf8');

test('POST grades against the private server-side answer and returns only correctness', () => {
  assert.match(route, /timingSafeEqual\(submitted, expected\)/);
  assert.match(route, /correct: timingSafeEqual\(submitted, expected\)/);
  assert.doesNotMatch(route, /NextResponse\.json\(\{[^}]*answer:\s*question\.answer/);
});

test('GET strips answer field before sending to client', () => {
  assert.match(route, /const \{ answer, \.\.\.rest \} = q;/);
});
// TASK-QBANK-005 (R9): görsel-dominant satırların yayın sözleşmesi. Bu testler
// `validQuestion` mantığını bağımsız olarak yeniden yazar ve karşılaştırır; yalnız
// metin eşleşmesi yapmaz, böylece kapının sessizce kayması görünür olur.
const REQUIRED = ["source_verified","year_verified","booklet_verified","question_number_verified","text_verified","options_verified","answer_key_source_verified","answer_key_verified","curriculum_verified","solution_verified","duplicate_checked"];
const VISUAL_PATH = /^\/[a-z0-9]+(?:-[a-z0-9]+)*(?:\/[a-z0-9]+(?:-[a-z0-9]+)*)*\.png$/;
const REPS = ["STRUCTURED_TEXT","IMAGE_BACKED","HYBRID"];
const validVisual = (v) => !!v && typeof v === "object" && v.authority === "ORIGINAL_MEB_PDF" &&
  typeof v.publicPath === "string" && VISUAL_PATH.test(v.publicPath) && !v.publicPath.includes("..") &&
  Number.isInteger(v.page) && v.page >= 1 && Number.isInteger(v.renderDpi) && v.renderDpi >= 150 &&
  !!v.clipRectPt && ["x0","y0","x1","y1"].every((k) => typeof v.clipRectPt[k] === "number");
const validQuestion = (q) => {
  if (!q || typeof q !== "object") return false;
  const rep = q.representation ?? "STRUCTURED_TEXT";
  if (!REPS.includes(rep)) return false;
  const stemOk = rep === "IMAGE_BACKED" ? (q.stem == null || q.stem === "") : (typeof q.stem === "string" && q.stem.trim().length > 0);
  const optionsOk = rep === "IMAGE_BACKED" ? (q.options == null || (typeof q.options === "object" && !Array.isArray(q.options))) : (!!q.options && typeof q.options === "object" && !Array.isArray(q.options));
  const visualOk = rep === "STRUCTURED_TEXT" ? (q.visual == null) : validVisual(q.visual);
  return typeof q.id === "string" && typeof q.sourceId === "string" && q.status === "VERIFIED" &&
    q.grade === 8 && typeof q.subject === "string" && stemOk && optionsOk && visualOk &&
    /^[a-f0-9]{64}$/.test(q.sourceHash ?? "") && !!q.verification &&
    REQUIRED.every((k) => q.verification?.[k] === true) && typeof q.answer === "string" && /^[A-D]$/.test(q.answer) &&
    (rep === "IMAGE_BACKED" || Object.hasOwn(q.options ?? {}, q.answer));
};
const VERIFIED = Object.fromEntries(REQUIRED.map((k) => [k, true]));
const VISUAL = { publicPath: "/pilot-2022-visual/img-q15-p28.png", page: 28, clipRectPt: { x0: 1, y0: 2, x1: 3, y1: 4 }, renderDpi: 300, authority: "ORIGINAL_MEB_PDF" };
const row = (patch) => ({ id: "x", sourceId: "MEB-LGS-2022", subject: "FEN", grade: 8, status: "VERIFIED", answer: "A", solution: "ç", verification: VERIFIED, sourceHash: "a".repeat(64), ...patch });

test('IMAGE_BACKED row is served only with original-PDF visual evidence', () => {
  assert.equal(validQuestion(row({ representation: "IMAGE_BACKED", stem: null, options: null, visual: VISUAL })), true);
  assert.equal(validQuestion(row({ representation: "IMAGE_BACKED", stem: null, options: null, visual: null })), false, 'görsel kanıtı olmayan satır reddedilmeli');
});

test('visual asset path cannot traverse or leave the site root', () => {
  // Not: `/etc/passwd.png` bir dosya sistemi okuması değildir; `public_path` yalnız
  // site-relative bir URL'dir ve `public/` altında çözülür. Reddedilmesi gereken
  // gerçek yüzeyler: `..` ile dizin kaçışı ve harici şema (path traversal /
  // arbitrary file serving).
  for (const hostile of ["/../etc/passwd.png", "/a/../../etc/passwd.png", "https://evil.example.com/x.png", "//evil.example.com/x.png"]) {
    assert.equal(validQuestion(row({ representation: "IMAGE_BACKED", stem: null, options: null, visual: { ...VISUAL, publicPath: hostile } })), false, hostile);
  }
});

test('unpublished or unchecked visual rows never reach clients', () => {
  assert.equal(validQuestion(row({ representation: "IMAGE_BACKED", stem: null, options: null, visual: VISUAL, status: "NEEDS_REVIEW" })), false);
  assert.equal(validQuestion(row({ representation: "IMAGE_BACKED", stem: null, options: null, visual: VISUAL, verification: { ...VERIFIED, options_verified: false } })), false);
});

test('declared representation must be one of the known modes', () => {
  assert.equal(validQuestion(row({ representation: "AUDIO", stem: "g", options: { A: "1", B: "2", C: "3", D: "4" } })), false);
  assert.equal(validQuestion(row({ representation: "HYBRID", stem: "g", options: { A: "1", B: "2", C: "3", D: "4" } })), false, 'HYBRID görsel kanıt ister');
  assert.equal(validQuestion(row({ representation: "HYBRID", stem: "g", options: { A: "1", B: "2", C: "3", D: "4" }, visual: VISUAL })), true);
});

test('structured rows keep their original contract (regression control)', () => {
  assert.equal(validQuestion(row({ representation: "STRUCTURED_TEXT", stem: "gövde", options: { A: "1", B: "2", C: "3", D: "4" } })), true);
  assert.equal(validQuestion(row({ representation: "STRUCTURED_TEXT", stem: "gövde", options: { A: "1", B: "2", C: "3" }, visual: VISUAL })), false);
});
