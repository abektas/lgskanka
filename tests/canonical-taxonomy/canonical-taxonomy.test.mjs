/**
 * Canonical H1–H7 tek-kaynak testi.
 *
 * Amaç: runtime'daki H1–H7 sözlüğünün `data/content.ts` → `errorTypes`
 * içinde **tek** tanımlı olduğunu ve türetilen istem sözlüğünün
 * doğru üretildiğini doğrular.
 *
 * Yetkili sözlük: `AGENTS.md` → "Error taxonomy: H1–H7".
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = (relative) => fs.readFileSync(new URL(relative, import.meta.url), 'utf8');

const contentSource = read('../../data/content.ts');

/** `data/content.ts`'deki canonical H1–H7 sözlüğü. */
const CANONICAL = [
  { code: 'H1', name: 'Kavram eksikliği', promptHint: 'kavram' },
  { code: 'H2', name: 'Yöntem / strateji', promptHint: 'yöntem/strateji' },
  { code: 'H3', name: 'Okuma / modelleme', promptHint: 'okuduğunu anlama/modelleme' },
  { code: 'H4', name: 'İşlem hatası', promptHint: 'işlem' },
  { code: 'H5', name: 'Gereksiz bilgi', promptHint: 'gereksiz bilgiyi ayıklama' },
  { code: 'H6', name: 'İlişkilendirme', promptHint: 'bilgileri ilişkilendirme' },
  { code: 'H7', name: 'Dikkat', promptHint: 'dikkat' },
];

/** `data/content.ts`'i çalıştırıp değerleri okur. */
async function loadContentModule() {
  return import(new URL('../../data/content.ts', import.meta.url).href);
}

test('errorTypes H1–H7 kodu, sırası ve benzersizliği canonical sözlükle eşleşir', async () => {
  const { errorTypes } = await loadContentModule();

  assert.deepEqual(
    errorTypes.map((item) => item.code),
    CANONICAL.map((item) => item.code),
    'H1..H7 eksiksiz, doğru sırada ve tekrarsız olmalı',
  );
  assert.equal(new Set(errorTypes.map((item) => item.code)).size, 7);

  for (const expected of CANONICAL) {
    const found = errorTypes.find((item) => item.code === expected.code);
    assert.ok(found, `${expected.code} errorTypes içinde bulunmalı`);
    assert.equal(found.name, expected.name, `${expected.code} adı canonical olmalı`);
    assert.equal(found.promptHint, expected.promptHint, `${expected.code} prompt etiketi canonical olmalı`);
  }
});

test('istem sözlüğü errorTypes\'ten türetilir ve doğru formattadır', async () => {
  const { errorCodePromptLine } = await loadContentModule();

  // Canonical format: "Hata kodlarından uygun olanı seç: H1 ..., H2 ..., ..."
  const expected = `Hata kodlarından uygun olanı seç: ${CANONICAL.map(
    (item) => `${item.code} ${item.promptHint}`,
  ).join(', ')}.`;

  assert.equal(
    errorCodePromptLine,
    expected,
    'Türetilen istem sözlüğü canonical format ile eşleşmeli',
  );
  assert.match(contentSource, /export const errorCodePromptLine = `Hata kodlarından uygun olanı seç: /);
});

test('data/content.ts tek H1–H7 sözlüğü tanımlar (ikinci kopya yok)', () => {
  // errorTypes dizisi sadece bir kez tanımlı olmalı
  const matches = contentSource.match(/export const errorTypes/g);
  assert.equal(matches?.length, 1, 'errorTypes sadece bir kez export edilmeli');

  // Elle yazılmış ikinci sözlük bulunmamalı (örn. H1 kavram, H2 ... satırı)
  assert.doesNotMatch(
    contentSource,
    /H1 kavram, H2 yöntem/,
    'Elle yazılmış H1–H7 sözlüğü satırı bulunmamalı (türetilmiş olmalı)',
  );
});

test('AGENTS.md canonical sözlüğü yedi kodu taşır', () => {
  const agents = read('../../AGENTS.md');
  for (const { code } of CANONICAL) {
    assert.ok(agents.includes(`**${code} —`), `AGENTS.md ${code} tanımını içermeli`);
  }
});