/**
 * Pekiştirme tespiti + günlük plan seçimi için davranış testleri.
 *
 * Çalıştır: npx tsx scripts/test-reinforcement.ts
 *
 * localStorage yok — testte bellek içi bir taklit kurulur; modüller yalnızca
 * çağrı anında localStorage'a dokunduğu için bu güvenli.
 */
import assert from "node:assert/strict";
import { computeWeakUnits, subjectWeakKey, syncReinforcementTasks, loadReinforcementTasks } from "../lib/reinforcement";
import { composeDailyPlan } from "../lib/daily-plan";

const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => void store.set(k, v),
  removeItem: (k: string) => void store.delete(k),
  clear: () => store.clear(),
};

type Rec = {
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
};

function rec(over: Partial<Rec> & { questionId: string; subject: string }): Rec {
  return {
    unit: null,
    unitName: null,
    topic: null,
    selectedAnswer: "A",
    correct: false,
    errorReasonCode: null,
    timeSpentSec: 10,
    source: "gunluk",
    createdAt: "2026-11-09T10:00:00.000Z",
    ...over,
  };
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

// 1) Günlük 5 soruda yanlışlar farklı ünitelere dağılsa bile ders görevi oluşur.
ok("zayıf ders, ünite eşiği tutmasa da görev üretir", () => {
  const records: Rec[] = [
    rec({ questionId: "m1", subject: "matematik", unit: 1, unitName: "Çarpanlar", topic: "EBOB" }),
    rec({ questionId: "m2", subject: "matematik", unit: 2, unitName: "Kareköklü", topic: "Kareköklü sayılar" }),
    rec({ questionId: "m3", subject: "matematik", unit: 3, unitName: "Veri", topic: "Grafik" }),
    rec({ questionId: "m4", subject: "matematik", unit: 1, unitName: "Çarpanlar", correct: true }),
    rec({ questionId: "m5", subject: "matematik", unit: 2, unitName: "Kareköklü", correct: true }),
  ];
  const weak = computeWeakUnits(records as any);
  const key = subjectWeakKey("matematik");
  assert.ok(weak.has(key), "ders düzeyi görev yok");
  const task = weak.get(key)!;
  assert.equal(task.subject, "matematik");
  assert.equal(task.count, 3);
  assert.ok(task.unit === 1 || task.unit === 2 || task.unit === 3, "en çok yanlış yapılan ünite seçilmeli");
});

// 2) Ünite kuralı korunur: aynı ünitede 3 yanlış → ünite görevi.
ok("aynı ünitede 3 yanlış ünite görevi üretir", () => {
  const records: Rec[] = [
    rec({ questionId: "f1", subject: "fen", unit: 4, unitName: "Madde" }),
    rec({ questionId: "f2", subject: "fen", unit: 4, unitName: "Madde" }),
    rec({ questionId: "f3", subject: "fen", unit: 4, unitName: "Madde" }),
    rec({ questionId: "f4", subject: "fen", unit: 4, unitName: "Madde", correct: true }),
  ];
  const weak = computeWeakUnits(records as any);
  assert.ok(weak.has("fen|4"), "ünite görevi yok: " + [...weak.keys()].join(","));
  // Ünite görevi varken aynı ders için ikinci bir ders görevi açılmaz.
  assert.equal(weak.has(subjectWeakKey("fen")), false);
});

// 3) Pekiştirme kayıtları tetikleyici değildir.
ok("pekistirme kayıtları yeni görev doğurmaz", () => {
  const records: Rec[] = [
    rec({ questionId: "p1", subject: "turkce", unit: 1, unitName: "Sözcükte Anlam", source: "pekistirme" }),
    rec({ questionId: "p2", subject: "turkce", unit: 1, unitName: "Sözcükte Anlam", source: "pekistirme" }),
    rec({ questionId: "p3", subject: "turkce", unit: 1, unitName: "Sözcükte Anlam", source: "pekistirme" }),
  ];
  const weak = computeWeakUnits(records as any);
  assert.equal(weak.size, 0);
});

// 4) Doğruluğu %60 ve üzeri olan ders zayıf sayılmaz.
ok("güçlü ders görev üretmez", () => {
  const records: Rec[] = [
    rec({ questionId: "d1", subject: "din-kulturu", unit: 1, unitName: "Kader", correct: true }),
    rec({ questionId: "d2", subject: "din-kulturu", unit: 1, unitName: "Kader", correct: true }),
    rec({ questionId: "d3", subject: "din-kulturu", unit: 2, unitName: "Zekât", correct: true }),
  ];
  assert.equal(computeWeakUnits(records as any).size, 0);
});

// 5) Bitmiş görev, sonrasında gelen yanlışla tazelenir ve yeni soru seti ister.
ok("tamamlanmış görev yeni yanlışta yeniden açılır", () => {
  store.clear();
  const completedAt = "2026-11-09T09:00:00.000Z";
  store.set(
    "lgs_reinforcement_tasks",
    JSON.stringify([
      {
        id: subjectWeakKey("turkce"),
        subject: "turkce",
        unit: 1,
        unitName: "Sözcükte Anlam",
        topic: "Sözcükte Anlam",
        source: "gunluk",
        wrongCount: 3,
        createdAt: completedAt,
        questionIds: ["q1", "q2", "q3", "q4", "q5"],
        answers: { q1: "A", q2: "B", q3: "C", q4: "D", q5: "A" },
        correctness: { q1: true, q2: true, q3: true, q4: true, q5: true },
        status: "tamamlandi",
        updatedAt: completedAt,
      },
    ])
  );
  store.set(
    "lgs_answer_log",
    JSON.stringify([
      rec({ questionId: "t1", subject: "turkce", unit: 1, unitName: "Sözcükte Anlam", createdAt: "2026-11-09T11:00:00.000Z" }),
      rec({ questionId: "t2", subject: "turkce", unit: 1, unitName: "Sözcükte Anlam", createdAt: "2026-11-09T11:05:00.000Z" }),
      rec({ questionId: "t3", subject: "turkce", unit: 2, unitName: "Cümlede Anlam", createdAt: "2026-11-09T11:10:00.000Z" }),
    ])
  );
  const tasks = syncReinforcementTasks();
  const task = tasks.find((t) => t.id === subjectWeakKey("turkce"))!;
  assert.equal(task.status, "bekliyor", "görev yeniden açılmalı");
  assert.deepEqual(task.questionIds, []);
  assert.deepEqual(task.answers, {});
  assert.ok((task.servedQuestionIds ?? []).includes("q1"));
  assert.equal(loadReinforcementTasks()[0].status, "bekliyor");
});

// 6) Günlük plan: kota korunur, zayıf ünite soruları öne alınır.
ok("günlük plan zayıf üniteyi öne alır ve 24 soruyu korur", () => {
  const limits: Record<string, number> = {
    turkce: 5,
    matematik: 5,
    fen: 5,
    "inkilap-tarihi": 3,
    "din-kulturu": 3,
    ingilizce: 3,
  };
  const pools: Record<string, any[]> = {};
  for (const subject of Object.keys(limits)) {
    pools[subject] = Array.from({ length: 20 }, (_, i) => ({
      id: `${subject}-${i}`,
      subject,
      unit: (i % 8) + 1,
      unitName: "Ünite " + ((i % 8) + 1),
    }));
  }
  const plan = composeDailyPlan(pools, limits, [{ subject: "matematik", unit: 6, unitName: null }]);
  assert.equal(plan.length, 24);
  for (const [subject, limit] of Object.entries(limits)) {
    assert.equal(plan.filter((q) => q.subject === subject).length, limit, subject + " kotası");
  }
  const firstMath = plan.find((q) => q.subject === "matematik")!;
  assert.equal(firstMath.unit, 6, "zayıf ünite sorusu önce gelmeli");
  assert.equal(new Set(plan.map((q) => q.id)).size, plan.length, "tekrar soru olmamalı");
});

// 7) Zayıf ünite yoksa sıra korunur (ünite artan).
ok("zayıf ünite yokken havuz sırası korunur", () => {
  const pools = { turkce: [
    { id: "a", subject: "turkce", unit: 1, unitName: null },
    { id: "b", subject: "turkce", unit: 2, unitName: null },
  ] };
  const plan = composeDailyPlan(pools as any, { turkce: 2 }, []);
  assert.deepEqual(plan.map((q) => q.id), ["a", "b"]);
});

console.log(`\n${passed} test geçti`);
