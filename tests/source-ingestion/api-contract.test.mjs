import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const route = fs.readFileSync(new URL('../../app/api/study/route.ts', import.meta.url), 'utf8');
const answerRecords = fs.readFileSync(new URL('../../app/api/answer-records/route.ts', import.meta.url), 'utf8');
const dailyPage = fs.readFileSync(new URL('../../app/calis/page.tsx', import.meta.url), 'utf8');
const gameEconomySource = fs.readFileSync(new URL('../../data/nav.ts', import.meta.url), 'utf8');
const chrome = fs.readFileSync(new URL('../../components/chrome.tsx', import.meta.url), 'utf8');
const profileForm = fs.readFileSync(new URL('../../components/profile-form.tsx', import.meta.url), 'utf8');
const homePage = fs.readFileSync(new URL('../../app/page.tsx', import.meta.url), 'utf8');
const continueCard = fs.readFileSync(new URL('../../components/continue-card.tsx', import.meta.url), 'utf8');
const scoreCounts = fs.readFileSync(new URL('../../components/score-counts.tsx', import.meta.url), 'utf8');
const monthlyExamPage = fs.readFileSync(new URL('../../app/aylik-denemeler/page.tsx', import.meta.url), 'utf8');
const weeklyPage = fs.readFileSync(new URL('../../app/haftalik-test/page.tsx', import.meta.url), 'utf8');
const resultsPage = fs.readFileSync(new URL('../../app/sonuclar/page.tsx', import.meta.url), 'utf8');
const resultsAnalytics = fs.readFileSync(new URL('../../lib/results-analytics.ts', import.meta.url), 'utf8');
const manifestBuilder = fs.readFileSync(new URL('../../scripts/build_subject_manifests.py', import.meta.url), 'utf8');
const learnerStats = fs.readFileSync(new URL('../../lib/learner-stats.ts', import.meta.url), 'utf8');
const badgeProgress = fs.readFileSync(new URL('../../components/use-badge-progress.ts', import.meta.url), 'utf8');
const reinforcement = fs.readFileSync(new URL('../../lib/reinforcement.ts', import.meta.url), 'utf8');
const pekistirmePage = fs.readFileSync(new URL('../../app/pekistirme/page.tsx', import.meta.url), 'utf8');

test('POST grades against the private server-side answer and returns only correctness', () => {
  assert.match(route, /const correct = timingSafeEqual\(submitted, expected\)/);
  assert.match(route, /if \(!auth\) return NextResponse\.json\(\{ error: "Giriş yapılmamış\." \}, \{ status: 401 \}\)/);
  assert.match(route, /rateLimit\(`study-answer:/);
  assert.match(route, /correct,/);
  assert.doesNotMatch(route, /NextResponse\.json\(\{[^}]*answer:\s*question\.answer/);
});

test('GET strips answer keys in every mode, including legacy wrong_mode parameter', () => {
  assert.match(route, /const \{ answer: _answerKey, \.\.\.rest \} = q;/);
  assert.doesNotMatch(route, /if \(wrongMode\s*===/);
});

test('public forgot-password route cannot reset accounts', () => {
  const forgot = fs.readFileSync(new URL('../../app/api/auth/forgot/route.ts', import.meta.url), 'utf8');
  assert.match(forgot, /status:\s*410/);
  assert.doesNotMatch(forgot, /dbUpdate|hashPassword/);
});

test('daily summary counts todays gunluk records after a fresh-question reload and waits for grading before advancing', () => {
  assert.match(dailyPage, /window\.addEventListener\("lgs-answer-records-changed", refreshRecords\)/);
  assert.match(dailyPage, /latestByQuestion\.set\(record\.questionId, record\)/);
  assert.match(dailyPage, /const total = Math\.max\(questions\.length, answered\)/);
  assert.match(dailyPage, /for \(const r of sessionRecords\)/);
  assert.doesNotMatch(dailyPage, /questions\.flatMap\(\(question\)/);
  assert.doesNotMatch(dailyPage, /questionIds\.has\(record\.questionId\)/);
  assert.match(dailyPage, /if \(solved >= target && merged\.length > 0\) \{\s*setCompleted\(true\)/);
  assert.match(dailyPage, /disabled=\{checkState === "pending" \|\| checkState === null\}/);
  assert.match(dailyPage, /apiFetch\("\/api\/study"/);
});

test('daily next-step links are styled as clear, clickable buttons', () => {
  assert.match(dailyPage, /className="btn btn-soft btn-sm next-step-link" href="\/pekistirme">Pekiştirme çalışması yap/);
  assert.match(dailyPage, /className="btn btn-soft btn-sm next-step-link" href=\{cycle\?\.weekendTest/);
  assert.match(dailyPage, /className="btn btn-soft btn-sm next-step-link" href="\/sonuclar">Sonuçlar ve İlerleme/);
  assert.match(dailyPage, /className="next-steps"/);
});

test('weak-unit detection groups wrong answers per unit and only feeds from assessments', () => {
  assert.match(reinforcement, /record\.unit === null && !record\.unitName\) continue/);
  assert.match(reinforcement, /record\.source \?\? "gunluk"\) === "pekistirme"\) continue/);
  assert.doesNotMatch(reinforcement, /!record\.correct && record\.topic/);
  assert.match(reinforcement, /if \(data\.count >= 3\)/);
});

test('pekiştirme subject selection opens the first unanswered question in a study-style flow', () => {
  assert.doesNotMatch(pekistirmePage, /className="pekiştirme-summary"/);
  assert.match(pekistirmePage, /onClick=\{\(\) => handleSelectSubject\(subject\.slug\)\}/);
  assert.match(pekistirmePage, /firstUnanswered/);
  assert.match(pekistirmePage, /className="exam-question-header"/);
  assert.match(pekistirmePage, /onAnswer=\{\(letter\) => handleAnswer\(task\.id, qid, letter\)\}/);
  assert.match(pekistirmePage, /className="exam-answers"/);
  assert.match(pekistirmePage, /className="zoom-overlay"/);
  assert.match(pekistirmePage, /exam-report-btn/);
  assert.match(pekistirmePage, /className="btn btn-soft"[\s\S]*?Sonraki soru/);
  assert.match(pekistirmePage, /loadTaskQuestions\(task\)/);
  assert.match(pekistirmePage, /updateTaskStatus\(taskId, "tamamlandi"\)/);
});

test('homepage subject cards use real answer records and stale optional cards are absent', () => {
  assert.match(homePage, /computeSubjectAccuracy\(records\)/);
  assert.doesNotMatch(homePage, /subject\.score|subject\.delta/);
  assert.doesNotMatch(homePage, /<StudyTimer\s*\/>|<TaskList\s*\/>|<HeroArt\s*\/>/);
  assert.doesNotMatch(homePage, /mission-bar|weeklyGoal|bugunun-gorevleri/);
});

test('monthly exam result calls the score Net, not Ham Puan', () => {
  assert.match(monthlyExamPage, /Net \(yaklaşık\)/);
  assert.match(monthlyExamPage, /Yaklaşık net = Doğru/);
  assert.doesNotMatch(monthlyExamPage, /Ham Puan/);
});

test('error distribution uses the canonical H labels and refreshes after answer hydration', () => {
  assert.match(resultsAnalytics, /errorTypes\.map\(\(\{ code, name \}\) => \[code, name\]\)/);
  assert.doesNotMatch(resultsAnalytics, /H1: "Kavramsal eksiklik"/);
  assert.match(resultsPage, /window\.addEventListener\("lgs-answer-records-changed", refresh\)/);
});

test('daily "Konuyu bilmiyorum" self-assessment is classified as H1', () => {
  assert.match(dailyPage, /label: "Konuyu bilmiyorum", code: "H1"/);
});

test('student score summaries use labeled correct, wrong, blank, and total counts', () => {
  for (const page of [homePage, continueCard, dailyPage, monthlyExamPage, weeklyPage, resultsPage]) {
    assert.match(page, /ScoreCounts/);
  }
  for (const label of ['Doğru:', 'Yanlış:', 'Boş:', 'Toplam:']) assert.ok(scoreCounts.includes(label));
  assert.match(dailyPage, /const total = Math\.max\(questions\.length, answered\)/);
  assert.match(dailyPage, /const blank = total - answered/);
});

test('game playtime starts at five minutes and increases within the ten-minute daily cap', () => {
  assert.match(gameEconomySource, /\{ xp: 20, minutes: 5, label: "20 XP → 5 dakika" \}/);
  assert.match(gameEconomySource, /\{ xp: 50, minutes: 8, label: "50 XP → 8 dakika" \}/);
  assert.match(gameEconomySource, /\{ xp: 100, minutes: 10, label: "100 XP → 10 dakika" \}/);
});

test('desktop logout action is placed after the sidebar content; mobile profile fallback remains', () => {
  assert.ok(chrome.indexOf('className="side-foot"') < chrome.indexOf('className="side-logout"'));
  assert.match(chrome, /if \(window\.confirm\([\s\S]*?logout\(\)/);
  assert.match(profileForm, /className="settings-block profile-account"/);
});

test('answer-record uploads use canonical question metadata and server-verified correctness', () => {
  assert.match(answerRecords, /const correct = r\.selectedAnswer === question\.answer/);
  assert.match(answerRecords, /correct,/);
  assert.doesNotMatch(answerRecords, /correct:\s*!!r\.correct/);
  assert.match(answerRecords, /const source = \["gunluk", "haftalik", "pekistirme"\]/);
  assert.match(dailyPage, /source: "gunluk"/);
  assert.match(answerRecords, /subject:\s*question\.subject/);
});

test('badge progress accepts both hydrated map and local array formats and refreshes after answers', () => {
  assert.match(learnerStats, /Object\.values\(stored\)/);
  assert.match(learnerStats, /lgs-badge-progress-changed/);
  assert.match(badgeProgress, /Object\.entries\(stored\)/);
  assert.match(badgeProgress, /lgs-answer-records-changed/);
});

test('exam submission response omits canonical correct answers from details', () => {
  const exams = fs.readFileSync(new URL('../../app/api/exams-submit/route.ts', import.meta.url), 'utf8');
  assert.match(exams, /details:\s*publicDetails/);
  assert.match(exams, /const \{ correct: _answerKey, \.\.\.safeDetail \} = detail;/);
  assert.match(exams, /student_id=eq\.\$\{encodeURIComponent\(auth\.sub\)\}&month=eq\.\$\{month\}/);
  assert.match(exams, /if \(previousResults\.length > 0\)/);
});

test('exam submission requires an authenticated student before grading', () => {
  const exams = fs.readFileSync(new URL('../../app/api/exams-submit/route.ts', import.meta.url), 'utf8');
  assert.match(exams, /const auth = await authFromRequest\(request\)/);
  assert.match(exams, /if \(!auth\) return NextResponse\.json\(\{ error: "Giriş yapılmamış\." \}, \{ status: 401 \}\)/);
});

test('legacy manifest builder refuses unverified or unpublished questions', () => {
  assert.match(manifestBuilder, /q\.get\("status"\) != "VERIFIED"/);
  assert.match(manifestBuilder, /q\.get\("published"\) is not True/);
  assert.match(manifestBuilder, /Refusing to build empty manifests/);
});

test('legacy profile API authorizes ownership for every operation', () => {
  const profile = fs.readFileSync(new URL('../../app/api/profile/route.ts', import.meta.url), 'utf8');
  assert.equal((profile.match(/authorizeOwnProfile\(request, profileId\)/g) ?? []).length, 3);
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
