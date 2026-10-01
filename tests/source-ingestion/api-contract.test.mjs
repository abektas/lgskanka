import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const route = fs.readFileSync(new URL('../../app/api/questions/route.ts', import.meta.url), 'utf8');

test('API source gates all rows on VERIFIED status and every separate review check', () => {
  assert.match(route, /q\.status === "VERIFIED"/);
  assert.match(route, /REQUIRED_CHECKS\.every\(\(key\) => q\.verification\?\.\[key\] === true\)/);
  assert.match(route, /"answer_key_source_verified", "answer_key_verified"/);
  assert.match(route, /q\.sourceType === "REAL_LGS"[\s\S]*q\.year as number\) < 2018/);
});

test('GET applies subject and curriculum filters and strips answer/security fields', () => {
  assert.match(route, /\(!subject \|\| q\.subject === subject\) && \(!layer \|\| q\.curriculum\.layer === layer\)/);
  assert.match(route, /items: items\.map\(toPublicQuestion\)/);
  assert.match(route, /answer: _answer, verification: _verification, sourceHash: _hash/);
});

test('POST grades against the private server-side answer and returns only correctness', () => {
  assert.match(route, /\(readQuestions\(\)\)\.find\(\(q\) => q\.id === questionId\)/);
  assert.match(route, /timingSafeEqual\(submitted, expected\)/);
  assert.match(route, /NextResponse\.json\(\{ correct: timingSafeEqual\(submitted, expected\) \}/);
  assert.doesNotMatch(route, /NextResponse\.json\(\{[^}]*answer:\s*question\.answer/);
});
