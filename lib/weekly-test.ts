/**
 * Haftalık test kompozisyonu (Master Plan §12) — AI'sız, kural tabanlı.
 *
 * Dağılım kuralı: %50 zayıf alanlar · %30 yeni öğrenilenler · %20 karma tekrar.
 * Ders kotası plan §12 örneği: Matematik 10, Türkçe 8, Fen 6, İngilizce 2,
 * Din 2, İnkılap 2 (toplam 30). Kategori yetersizse diğer kategorilerden
 * tamamlanır; kota aşmaz.
 */
import type { AnswerRecord } from "./error-reason";
import type { UnitMastery } from "./mastery";

export type TestCategory = "zayif" | "yeni" | "karma";

export type TestQuestion = {
  id: string;
  subject: string;
  unit: number | null;
  unitName: string | null;
  topic: string | null;
  questionNumber: number;
  imagePath: string;
};

export type TestItem = {
  question: TestQuestion;
  category: TestCategory;
};

/** Plan §12 ders kotası — toplam 45 soru. */
export const SUBJECT_QUOTA: Record<string, number> = {
  turkce: 10,
  matematik: 10,
  fen: 10,
  "inkilap-tarihi": 5,
  "din-kulturu": 5,
  ingilizce: 5,
};

const RECENT_DAYS = 7;

function unitKey(q: { subject: string; unit: number | null }): string {
  return `${q.subject}|${q.unit ?? "-"}`;
}

/**
 * Ünite kategorisi (kural):
 * - zayıf: ustalık "zayıf"/"gelişiyor" veya tekrar zamanı gelmiş
 * - yeni: son 7 günde cevaplanmış, zayıf değil
 * - karma: diğerleri (hiç dokunulmamış konular dâhil)
 */
function unitCategory(
  key: string,
  masteryByKey: Map<string, UnitMastery>,
  lastAnswerByKey: Map<string, string>,
  now: Date
): TestCategory {
  const m = masteryByKey.get(key);
  if (m && (m.level === "zayıf" || m.level === "gelişiyor" || m.due)) return "zayif";
  const last = lastAnswerByKey.get(key);
  if (last) {
    const days = (now.getTime() - new Date(last).getTime()) / (24 * 60 * 60 * 1000);
    if (days <= RECENT_DAYS) return "yeni";
  }
  return "karma";
}

/**
 * 45 soruluk haftalık testi kurar.
 * Mantık: Hafta içi (Pzt–Cum) günlük çalışmalarda YAPAMADIĞI (yanlış yaptığı)
 * ders/konular öncelikli sorulur. Yapamadığı konu yoksa aynı seviyede başka
 * sorular konur. Saf fonksiyondur: aynı havuz + kayıtlar aynı kompozisyonu verir.
 */
export function composeWeeklyTest(
  pool: TestQuestion[],
  masteries: UnitMastery[],
  records: AnswerRecord[],
  now: Date = new Date()
): TestItem[] {
  const masteryByKey = new Map(masteries.map((m) => [unitKey(m), m]));

  // Son 7 günde yanlış yapılan konuları tespit et
  const weekAgo = now.getTime() - 7 * 24 * 60 * 60 * 1000;
  const wrongCountByKey = new Map<string, number>();
  const lastAnswerByKey = new Map<string, string>();
  for (const r of records) {
    const key = unitKey(r);
    const prev = lastAnswerByKey.get(key);
    if (!prev || r.createdAt > prev) lastAnswerByKey.set(key, r.createdAt);
    if (!r.correct && new Date(r.createdAt).getTime() >= weekAgo) {
      wrongCountByKey.set(key, (wrongCountByKey.get(key) ?? 0) + 1);
    }
  }

  const items: TestItem[] = [];
  for (const [subject, quota] of Object.entries(SUBJECT_QUOTA)) {
    const candidates = pool
      .filter((q) => q.subject === subject)
      .map((q) => {
        const key = unitKey(q);
        // Yapamadı: son 7 günde yanlış yapılan konu
        const isWrong = (wrongCountByKey.get(key) ?? 0) > 0;
        let category: TestCategory;
        if (isWrong) {
          category = "zayif"; // yapamadığı konu
        } else {
          const last = lastAnswerByKey.get(key);
          if (last) {
            const days = (now.getTime() - new Date(last).getTime()) / (24 * 60 * 60 * 1000);
            category = days <= RECENT_DAYS ? "yeni" : "karma";
          } else {
            category = "karma"; // hiç dokunulmamış
          }
        }
        return { question: q, category };
      });

    // Yapamadı → yeni → karma sırasıyla doldur
    const byCategory = (cat: TestCategory) =>
      candidates
        .filter((c) => c.category === cat)
        .sort((a, b) => {
          // Yapamadıklarında: çok yanlış yapılan önce
          const wrongA = wrongCountByKey.get(unitKey(a.question)) ?? 0;
          const wrongB = wrongCountByKey.get(unitKey(b.question)) ?? 0;
          if (wrongA !== wrongB) return wrongB - wrongA;
          return a.question.id.localeCompare(b.question.id);
        });

    const items: TestItem[] = [];
    for (const cat of ["zayif", "yeni", "karma"] as const) {
      for (const c of byCategory(cat)) {
        if (items.length >= quota) break;
        if (items.some((p) => p.question.id === c.question.id)) continue;
        items.push(c);
      }
      if (items.length >= quota) break;
    }
    items.push(...items);
  }
  return items;
}

export const CATEGORY_LABELS: Record<TestCategory, string> = {
  zayif: "Yapamadığın konu",
  yeni: "Yeni çalıştığın",
  karma: "Genel tekrar",
};

/** Pazar telafi testi kotaları (günlük çalışma ile aynı: 24 soru). */
export const TELAFI_QUOTA: Record<string, number> = {
  turkce: 5,
  matematik: 5,
  fen: 5,
  "inkilap-tarihi": 3,
  "din-kulturu": 3,
  ingilizce: 3,
};

/**
 * Pazar telafi testi (24 soru) — haftanın yanlışlarını kapatır.
 * Kaynaklar:
 *  - Son 7 gündeki günlük çalışma yanlışları (cevap kayıtları)
 *  - Bu haftanın Cumartesi haftalık testi yanlışları
 * Strateji: Önce tam yanlış yapılan soruları (varsa havuzda), sonra aynı ünite/konu.
 * Kategori: "telafi" (kesin yanlış), "genel" (doldurma).
 */
export type TelafiCategory = "telafi" | "genel";

export type TelafiItem = {
  question: TestQuestion;
  category: TelafiCategory;
};

/**
 * 24 soruluk Pazar Telafi testi kurar.
 * Kaynaklar:
 * - records: son 7 gündeki günlük cevap kayıtları (AnswerRecord[])
 * - weeklyWrongIds: bu hafta Cumartesi haftalık testi yanlışları
 * - pool: mevcut soru havuzu (TestQuestion[])
 */
export function composeTelafiTest(
  pool: TestQuestion[],
  records: { createdAt: string; correct: boolean; questionId: string; subject: string; unit: number | null; unitName: string | null; topic: string | null }[],
  weeklyWrongIds: Set<string>,
  now: Date = new Date()
): { question: TestQuestion; category: "telafi" | "genel" }[] {
  // 1) Son 7 gündeki günlük yanlışları topla (questionId bazında)
  const dailyWrongIds = new Set<string>();
  for (const r of records) {
    if (!r.correct && new Date(r.createdAt).getTime() >= now.getTime() - 7 * 24 * 60 * 60 * 1000) {
      dailyWrongIds.add(r.questionId);
    }
  }

  // 2) Haftalık test yanlışları + günlük yanlışlar birleşimi
  const allWrongIds = new Set([...dailyWrongIds, ...weeklyWrongIds]);

  // 3) Pool içinde bu ID'lerle eşleşen soruları "telafi" kategorisinde topla
  const telafiBySubject: Record<string, { id: string; question: TestQuestion }[]> = {};
  for (const q of pool) {
    if (allWrongIds.has(q.id)) {
      if (!telafiBySubject[q.subject]) telafiBySubject[q.subject] = [];
      telafiBySubject[q.subject].push({ id: q.id, question: q });
    }
  }

  // 4) Aynı subject'ten "genel" doldurma adayları
  const fillerBySubject: Record<string, typeof pool> = {};
  for (const q of pool) {
    if (!allWrongIds.has(q.id)) {
      if (!fillerBySubject[q.subject]) fillerBySubject[q.subject] = [];
      fillerBySubject[q.subject].push(q);
    }
  }

  const items: { question: TestQuestion; category: "telafi" | "genel" }[] = [];

  for (const [subject, quota] of Object.entries(TELAFI_QUOTA)) {
    const telafiCandidates = telafiBySubject[subject] || [];
    const fillerCandidates = fillerBySubject[subject] || [];

    const picked: { question: TestQuestion; category: "telafi" | "genel" }[] = [];

    // Önce tam yanlışlar (telafi)
    for (const c of telafiCandidates) {
      if (picked.length >= (TELAFI_QUOTA as Record<string, number>)[subject]) break;
      if (picked.some((p) => p.question.id === c.id)) continue;
      picked.push({ question: c.question, category: "telafi" });
    }

    // Sonra filler (genel) — aynı subject'ten
    for (const q of fillerCandidates) {
      if (picked.length >= (TELAFI_QUOTA as Record<string, number>)[subject]) break;
      if (picked.some((p) => p.question.id === q.id)) continue;
      picked.push({ question: q, category: "genel" });
    }

    items.push(...picked);
  }

  return items.map((i) => ({ question: i.question, category: i.category }));
}

/** Pazar telafi kategori etiketleri. */
export const TELAFI_CATEGORY_LABELS: Record<"telafi" | "genel", string> = {
  telafi: "Bu hafta yanlış yaptığın",
  genel: "Genel tekrar",
};