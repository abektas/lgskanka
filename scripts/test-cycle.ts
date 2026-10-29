/**
 * Döngü motoru testi — hafta sonu esnekliği ve 4 haftalık ritim.
 * Çalıştır: npx tsx scripts/test-cycle.ts
 */
import { computeCycleState, cycleSummary } from "../lib/cycle";

/** 2026-10-26 = Pazartesi. */
const enrollment = new Date("2026-10-26T09:00:00");

function d(iso: string) {
  return new Date(iso);
}

let failures = 0;
function check(label: string, actual: unknown, expected: unknown) {
  const ok = actual === expected;
  if (!ok) failures++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${label}  →  ${actual}${ok ? "" : ` (beklenen: ${expected})`}`);
}

console.log("--- Kayıt: 26.10.2026 Pazartesi ---");

// Hafta 1: Pzt 26, Çar 28, Cmt 31, Paz 1 Kas
let s = computeCycleState(d("2026-10-26T10:00:00"), enrollment);
check("Pzt 26.10 gün tipi", s.dayType, "gunluk");
check("Pzt 26.10 döngü haftası", s.cycleWeek, 1);
check("Pzt 26.10 döngü numarası", s.cycleNumber, 1);

s = computeCycleState(d("2026-10-28T10:00:00"), enrollment);
check("Çar 28.10 gün tipi", s.dayType, "gunluk");

s = computeCycleState(d("2026-10-31T10:00:00"), enrollment);
check("Cmt 31.10 gün tipi", s.dayType, "haftalik");
check("Cmt 31.10 hafta sonu testi", s.weekendTest, "haftalik");
check("Cmt 31.10 döngü haftası", s.cycleWeek, 1);
check("Cmt 31.10 hafta sonu mu", s.isWeekend, true);

s = computeCycleState(d("2026-11-01T10:00:00"), enrollment);
check("Paz 01.11 gün tipi (haftalık test sadece cumartesi)", s.dayType, "gunluk");
check("Paz 01.11 döngü haftası (cumartesiyle aynı)", s.cycleWeek, 1);
check("Paz 01.11 cumartesi değil", s.isSaturday, false);

console.log("\n--- Hafta 2: 2-8 Kas ---");
s = computeCycleState(d("2026-11-07T10:00:00"), enrollment);
check("Cmt 07.11 gün tipi", s.dayType, "haftalik");
check("Cmt 07.11 döngü haftası", s.cycleWeek, 2);
s = computeCycleState(d("2026-11-08T10:00:00"), enrollment);
check("Paz 08.11 gün tipi (haftalık sadece cumartesi)", s.dayType, "gunluk");
check("Paz 08.11 döngü haftası", s.cycleWeek, 2);

console.log("\n--- Hafta 3: 9-15 Kas ---");
s = computeCycleState(d("2026-11-14T10:00:00"), enrollment);
check("Cmt 14.11 gün tipi", s.dayType, "haftalik");
check("Cmt 14.11 döngü haftası", s.cycleWeek, 3);

console.log("\n--- Hafta 4: 16-22 Kas → AYLIK DENEME ---");
s = computeCycleState(d("2026-11-21T10:00:00"), enrollment);
check("Cmt 21.11 gün tipi", s.dayType, "aylik");
check("Cmt 21.11 hafta sonu testi", s.weekendTest, "aylik");
check("Cmt 21.11 döngü haftası", s.cycleWeek, 4);
check("Cmt 21.11 döngü numarası (hâlâ 1)", s.cycleNumber, 1);

s = computeCycleState(d("2026-11-22T10:00:00"), enrollment);
check("Paz 22.11 gün tipi", s.dayType, "aylik");
check("Paz 22.11 döngü haftası", s.cycleWeek, 4);

console.log("\n--- 2. döngü: 23-29 Kas (1. hafta), 30 Kas-6 Ara (2.) ---");
s = computeCycleState(d("2026-11-28T10:00:00"), enrollment);
check("Cmt 28.11 döngü haftası (yeni döngü 1. hafta)", s.cycleWeek, 1);
check("Cmt 28.11 döngü numarası", s.cycleNumber, 2);
check("Cmt 28.11 hafta sonu testi", s.weekendTest, "haftalik");

s = computeCycleState(d("2026-12-05T10:00:00"), enrollment);
check("Cmt 05.12 döngü haftası (2. döngünün 2. haftası)", s.cycleWeek, 2);
check("Cmt 05.12 döngü numarası", s.cycleNumber, 2);
check("Cmt 05.12 gün tipi", s.dayType, "haftalik");

console.log("\n--- 2. döngünün 4. haftası: 14-20 Ara → AYLIK DENEME ---");
s = computeCycleState(d("2026-12-19T10:00:00"), enrollment);
check("Cmt 19.12 döngü haftası (4. hafta)", s.cycleWeek, 4);
check("Cmt 19.12 döngü numarası", s.cycleNumber, 2);
check("Cmt 19.12 gün tipi", s.dayType, "aylik");
check("Paz 20.12 de aylık deneme", computeCycleState(d("2026-12-20T10:00:00"), enrollment).dayType, "aylik");

console.log("\n--- 3. döngü başlangıcı: 21-27 Ara ---");
s = computeCycleState(d("2026-12-26T10:00:00"), enrollment);
check("Cmt 26.12 döngü haftası", s.cycleWeek, 1);
check("Cmt 26.12 döngü numarası", s.cycleNumber, 3);

console.log("\n--- Özet metni ---");
console.log(cycleSummary(computeCycleState(d("2026-10-31T10:00:00"), enrollment)));
console.log(cycleSummary(computeCycleState(d("2026-11-22T10:00:00"), enrollment)));
console.log(cycleSummary(computeCycleState(d("2026-11-18T10:00:00"), enrollment)));

console.log(`\n${failures === 0 ? "TÜM TESTLER GEÇTİ" : `${failures} TEST BAŞARISIZ`}`);
process.exit(failures === 0 ? 0 : 1);
