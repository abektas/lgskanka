/**
 * Haftalık test arşivi + aylık açıklık kuralları — davranış testleri.
 *
 * Çalıştır: npx tsx scripts/test-weekly-archive.ts
 *
 * localStorage taklit edilir; modüller yalnızca çağrı anında okur.
 */
import assert from "node:assert/strict";

const store = new Map<string, string>();
(globalThis as any).window = globalThis;
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => void store.set(k, v),
  removeItem: (k: string) => void store.delete(k),
  clear: () => store.clear(),
};

import {
  weeklyTestWeeks,
  openWeeklyTestWeeks,
  hasUnfinishedWeeklyTest,
  weekKey,
  dayKey,
  isMonthUnlocked,
} from "../lib/cycle";
import { composeWeeklyTest } from "../lib/weekly-test";
import { getWeeklyTestSet, saveWeeklyTestSet } from "../lib/weekly-test-sets";
import { weeklyTestRecordForWeek, completedWeeklyTestWeekKeys } from "../lib/weekly-test-history";

function reset() {
  store.clear();
}

/** Seviye tespiti `doneIso` tarihinde bitmiş + kayıt `enrolledIso` tarihinde. */
function seed(enrolledIso: string, doneIso: string) {
  store.set("lgs_enrollment_date", enrolledIso);
  store.set("lgs_cycle_anchor", doneIso);
  store.set(
    "lgs_exam_history",
    JSON.stringify([
      {
        date: doneIso,
        month: 0,
        monthName: "00_seviye_tespit",
        total: 40,
        correct: 20,
        wrong: 10,
        empty: 10,
        percentage: 50,
        level: "orta",
        bySubject: {},
        details: [],
      },
    ])
  );
}

let passed = 0;
function ok(name: string, fn: () => void) {
  try {
    fn();
    passed++;
    console.log("ok  -", name);
  } catch (e) {
    console.error("FAIL -", name);
    throw e;
  }
}

// 1) Cumartesi anahtarı pazartesi→cumartesi aynı hafta, pazar→aynı hafta.
ok("hafta anahtarı cumartesiye sabitlenir", () => {
  const monday = new Date(2026, 10, 2); // 2 Kasım 2026 Pazartesi
  const sunday = new Date(2026, 10, 8); // 8 Kasım Pazar
  const saturday = new Date(2026, 10, 7);
  assert.equal(dayKey(saturday), "2026-11-07");
  assert.equal(weekKey(monday), "2026-11-07");
  assert.equal(weekKey(sunday), "2026-11-07");
  assert.equal(weekKey(saturday), "2026-11-07");
});

// 2) Geçmiş haftalar kapanmaz, gelecek hafta kilitli.
ok("geçmiş haftalık testler açık kalır, gelecek hafta kilitli", () => {
  reset();
  // Seviye tespiti 2 Kasım Pazartesi bitti, kayıt 1 Kasım.
  seed(new Date(2026, 10, 1, 10).toISOString(), new Date(2026, 10, 2, 10).toISOString());
  const now = new Date(2026, 10, 18, 10); // 18 Kasım Çarşamba (4. döngü haftası değil, 3. hafta)
  const weeks = weeklyTestWeeks(now);
  assert.ok(weeks.length >= 3, "en az 3 hafta: " + weeks.length);
  const first = weeks[0];
  assert.equal(first.weekKey, "2026-11-07", "ilk haftalık test 7 Kasım cumartesi");
  assert.ok(weeks.filter((w) => w.open).length >= 2, "geçmiş haftalar açık olmalı");
  const future = weeks.find((w) => !w.open && !w.monthly);
  assert.ok(future, "gelecek hafta listelenmeli");
  assert.ok(future!.saturday.getTime() > now.getTime(), "gelecek hafta gerçekten ileride");
});

// 3) Cumartesi gelmeden o haftanın testi açılmaz (bugün Çarşamba).
ok("bugünün haftası cumartesiden önce açılmaz", () => {
  reset();
  seed(new Date(2026, 10, 1, 10).toISOString(), new Date(2026, 10, 2, 10).toISOString());
  const wednesday = new Date(2026, 10, 11, 10); // 11 Kasım Çarşamba
  const open = openWeeklyTestWeeks(wednesday);
  const currentKey = weekKey(wednesday); // 2026-11-14
  assert.equal(open.some((w) => w.weekKey === currentKey), false, "bu hafta henüz açılmamalı");
  assert.ok(open.length >= 1, "önceki hafta açık olmalı");
});

// 4) Cumartesi/pazar açılır.
ok("cumartesi ve pazar açılır", () => {
  for (const day of [7, 8]) {
    reset();
    seed(new Date(2026, 10, 1, 10).toISOString(), new Date(2026, 10, 2, 10).toISOString());
    const now = new Date(2026, 10, day, 10);
    const open = openWeeklyTestWeeks(now);
    assert.ok(open.some((w) => w.weekKey === weekKey(now)), `${day} Kasım'da bu hafta açık olmalı`);
  }
});

// 5) 4. hafta (aylık deneme) haftalık test listesine girmez.
ok("aylık deneme haftası haftalık listeye girmez", () => {
  reset();
  seed(new Date(2026, 10, 1, 10).toISOString(), new Date(2026, 10, 2, 10).toISOString());
  const now = new Date(2026, 10, 30, 10); // 30 Kasım Pazartesi → 4 hafta geçti
  const open = openWeeklyTestWeeks(now);
  assert.equal(open.some((w) => w.monthly), false);
  const all = weeklyTestWeeks(now);
  assert.ok(all.some((w) => w.monthly), "aylık hafta listede işaretli olmalı");
});

// 6) Kayıt tarihinden önce hafta üretilmez (kayıt 20 Kasım ise 7 Kasım yok).
ok("kayıt tarihinden önceki haftalar üretilmez", () => {
  reset();
  const enrolled = new Date(2026, 10, 20, 10); // 20 Kasım Cuma
  seed(enrolled.toISOString(), new Date(2026, 10, 21, 10).toISOString());
  const weeks = weeklyTestWeeks(new Date(2026, 11, 5, 10), enrolled);
  assert.equal(weeks[0].weekKey, "2026-11-28", "ilk hafta 28 Kasım olmalı, gelen: " + weeks[0].weekKey);
});

// 7) Çözülmemiş hafta tespiti.
ok("çözülmemiş açık hafta tespit edilir", () => {
  reset();
  seed(new Date(2026, 10, 1, 10).toISOString(), new Date(2026, 10, 2, 10).toISOString());
  const now = new Date(2026, 10, 18, 10);
  assert.equal(hasUnfinishedWeeklyTest([], now), true);
  assert.equal(hasUnfinishedWeeklyTest(openWeeklyTestWeeks(now).map((w) => w.weekKey), now), false);
});

// 8) Aylık deneme: süresi geçtikten sonra da açık kalır.
ok("aylık denemeler süresi geçse de açık kalır", () => {
  reset();
  const anchor = new Date(2026, 8, 1, 10); // 1 Eylül
  store.set("lgs_cycle_anchor", anchor.toISOString());
  assert.equal(isMonthUnlocked(0, anchor), true);
  // Zaman geçtikçe açılan ay KAPANMAZ: kapı yalnızca alt sınır koyar.
  assert.equal(isMonthUnlocked(1, anchor), true, "geçmiş ay açık kalmalı");
  // Henüz zamanı gelmemiş ay kilitli kalır.
  assert.equal(isMonthUnlocked(6, anchor), false, "gelecek ay kilitli olmalı");
});

// 9) 45 soruluk test gerçekten üretilir (kota korunur).
ok("haftalık test 45 soru üretir", () => {
  const pool: any[] = [];
  for (const s of ["turkce", "matematik", "fen", "inkilap-tarihi", "din-kulturu", "ingilizce"]) {
    for (let i = 0; i < 30; i++) {
      pool.push({
        id: `${s}-${i}`,
        subject: s,
        unit: (i % 6) + 1,
        unitName: "Ünite " + ((i % 6) + 1),
        topic: null,
        questionNumber: i + 1,
        imagePath: "/x.png",
      });
    }
  }
  const items = composeWeeklyTest(pool, [], [], new Date(2026, 10, 7));
  assert.equal(items.length, 45);
  const counts: Record<string, number> = {};
  for (const it of items) counts[it.question.subject] = (counts[it.question.subject] ?? 0) + 1;
  assert.equal(counts["turkce"], 10);
  assert.equal(counts["matematik"], 10);
  assert.equal(counts["fen"], 10);
  assert.equal(counts["ingilizce"], 5);
  assert.equal(new Set(items.map((i) => i.question.id)).size, 45, "tekrar soru olmamalı");
});

// 10) Soru seti haftaya bağlı saklanır ve aynen geri gelir.
ok("haftanın soru seti saklanır ve aynı sorular döner", () => {
  reset();
  const items = [
    { question: { id: "q1", subject: "turkce", unit: 1, unitName: null, topic: null, questionNumber: 1, imagePath: "/a.png" }, category: "zayif" as const },
  ];
  saveWeeklyTestSet("2026-11-07", items);
  const back = getWeeklyTestSet("2026-11-07");
  assert.ok(back);
  assert.equal(back!.items[0].question.id, "q1");
  // İkinci yazma mevcut seti ezmez
  saveWeeklyTestSet("2026-11-07", []);
  assert.equal(getWeeklyTestSet("2026-11-07")!.items.length, 1);
});

// 11) Eski kayıtlar weekKey olmadan da haftaya bağlanır.
ok("eski kayıtlar tarihten hafta anahtarı türetir", () => {
  reset();
  store.set(
    "lgs_weekly_test_history",
    JSON.stringify([
      {
        date: new Date(2026, 10, 8, 12).toISOString(), // 8 Kasım Pazar
        total: 45,
        correct: 20,
        wrong: 20,
        blank: 5,
        byCategory: { zayif: { total: 45, correct: 20 }, yeni: { total: 0, correct: 0 }, karma: { total: 0, correct: 0 } },
        weakUnits: [],
        questionIds: [],
      },
    ])
  );
  assert.deepEqual(completedWeeklyTestWeekKeys(), ["2026-11-07"]);
  assert.ok(weeklyTestRecordForWeek("2026-11-07"));
  assert.equal(weeklyTestRecordForWeek("2026-11-14"), null);
});

console.log(`\n${passed} test geçti`);
