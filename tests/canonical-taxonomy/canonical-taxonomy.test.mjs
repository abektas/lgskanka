/**
 * Canonical H1–H7 tek-kaynak testi (T5).
 *
 * Amaç: runtime'daki H1–H7 sözlüğünün `data/content.ts` → `errorTypes`
 * içinde **tek** tanımlı olduğunu ve türetilen istem sözlüğünün (a) mevcut
 * davranışla birebir aynı, (b) `app/api/ai/route.ts` içinde ikinci bir
 * elle yazılmış sözlük olarak tekrarlanmadığını doğrular.
 *
 * Yetkili sözlük: `AGENTS.md` → "Error taxonomy: H1–H7" ve Master Plan §6.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = (relative) => fs.readFileSync(new URL(relative, import.meta.url), 'utf8');

const contentSource = read('../../data/content.ts');
const routeSource = read('../../app/api/ai/route.ts');
const derslerSource = read('../../app/dersler/page.tsx');

/** Master Plan §6 ve `data/content.ts` promptHint değerleriyle hizalı canonical sözlük. */
const CANONICAL = [
  { code: 'H1', name: 'Kavram eksikliği', promptHint: 'kavram', masterPlan: 'Kavramsal eksiklik' },
  { code: 'H2', name: 'Yöntem / strateji', promptHint: 'yöntem/strateji', masterPlan: 'Yöntem / strateji eksikliği' },
  { code: 'H3', name: 'Okuma / modelleme', promptHint: 'okuduğunu anlama/modelleme', masterPlan: 'Okuma / anlama / modelleme' },
  { code: 'H4', name: 'İşlem hatası', promptHint: 'işlem', masterPlan: 'Hesaplama / işlem hatası' },
  { code: 'H5', name: 'Gereksiz bilgi', promptHint: 'gereksiz bilgiyi ayıklama', masterPlan: 'Gereksiz bilgiyi filtreleyememe' },
  { code: 'H6', name: 'İlişkilendirme', promptHint: 'bilgileri ilişkilendirme', masterPlan: 'Bilgileri ilişkilendirememe' },
  { code: 'H7', name: 'Dikkat', promptHint: 'dikkat', masterPlan: 'Dikkat / acele / rastgelelik' },
];

/**
 * `data/content.ts`'i gerçekten çalıştırıp değerleri okur (statik regex değil).
 * Node ≥ 22.18 yerleşik tip soyması sayesinde `.ts` doğrudan import edilir;
 * ek derleme adımı veya yeni bağımlılık gerekmez.
 */
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

test('istem sözlüğü errorTypes\'ten türetilir ve eski davranışla birebir aynıdır', async () => {
  const { errorCodePromptLine } = await loadContentModule();

  // T5 öncesi route.ts içinde elle yazılmış satır — kayma tespiti için sabit.
  const legacy = 'Hata kodlarından uygun olanı seç: H1 kavram, H2 yöntem/strateji, H3 okuduğunu anlama/modelleme, H4 işlem, H5 gereksiz bilgiyi ayıklama, H6 bilgileri ilişkilendirme, H7 dikkat.';

  assert.equal(
    errorCodePromptLine,
    legacy,
    'Türetilen istem sözlüğü, T5 öncesi elle yazılmış sözlükle birebir aynı olmalı (davranış değişmez)',
  );
  assert.match(contentSource, /export const errorCodePromptLine = `Hata kodlarından uygun olanı seç: \$\{errorTypes\.map\(/);
});

test('route.ts ikinci bir H1–H7 sözlüğü tanımlamaz, türetilmiş kaynağı kullanır', () => {
  assert.match(
    routeSource,
    /import \{ errorCodePromptLine \} from "\.\.\/\.\.\/\.\.\/data\/content"/,
    'route.ts canonical istem sözlüğünü data/content\'ten almalı',
  );
  assert.match(routeSource, /\$\{errorCodePromptLine\}/, 'buildPrompt türetilmiş sözlüğü kullanmalı');

  for (const { code, promptHint } of CANONICAL) {
    assert.doesNotMatch(
      routeSource,
      new RegExp(`${code}\\s+${promptHint}`),
      `route.ts içinde elle yazılmış "${code} ${promptHint}" sözlüğü bulunmamalı`,
    );
  }
  assert.doesNotMatch(routeSource, /Hata kodlarından uygun olanı seç:/);
});

test('dersler sayfası dizi indeksine değil H koduna göre eşleşir', () => {
  assert.doesNotMatch(derslerSource, /errorTypes\[\s*\d+\s*\]/, 'errorTypes[n] indeks erişimi olmamalı');
  assert.match(derslerSource, /find\(\(item\) => item\.code === code\)/);
  assert.match(derslerSource, /errorTypeLabel\("H1"\)/);
  assert.match(derslerSource, /errorTypeLabel\("H4"\)/);
});

test('AGENTS.md canonical sözlüğü Master Plan §6 ile aynı yedi kodu taşır', () => {
  const agents = read('../../AGENTS.md');
  for (const { code, masterPlan } of CANONICAL) {
    assert.ok(agents.includes(`**${code} —`), `AGENTS.md ${code} tanımını içermeli`);
    assert.ok(agents.includes(masterPlan), `AGENTS.md "${masterPlan}" ifadesini (Master Plan §6 karşılığı) içermeli`);
  }
  assert.doesNotMatch(
    agents,
    /H[2-7] — (Misconception|Strategy\/method selection|Procedure\/calculation|Attention\/working discipline|Time\/exam management)/,
    'Eski jenerik sözlük geri getirilmemeli',
  );
});