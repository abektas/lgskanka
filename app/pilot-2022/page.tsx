import type { Metadata } from "next";
import Link from "next/link";
import staging from "../../scripts/source-ingestion/data/questions/staging/MEB-LGS-2022__SAYISAL.json";

export const metadata: Metadata = {
  title: "2022 Pilot İnceleme",
  robots: { index: false, follow: false },
};

type Record_ = (typeof staging.records)[number];

/**
 * Gözden geçirme ekranı resmî MEB 2022 Sayısal "A" kitapçığından çıkarılan
 * adayları gösterir. Bu bir yayınlama yüzeyi DEĞİLDİR:
 *  - kayıtlar `NEEDS_REVIEW` / `published=false` durumundadır;
 *  - resmî cevap anahtarı bilerek gizlenir (PO incelemesi içindir, öğrenci
 *    ekranında görünmemelidir);
 *  - eksik alanlar (müfredat, çözüm, doğrulama) açıkça listelenir.
 */
export default function Pilot2022Page() {
  const { records, answer_key_summary, review_reasons } = staging;
  // TASK-QBANK-011: restored b425500 baseline has no
  // `unparsed_question_numbers` (QBANK-002-era field). Treat as optional;
  // never invent entries — missing means "no recorded orphans".
  type UnparsedRow = { subject: string; question_number: number; page: number };
  const unparsed_question_numbers: UnparsedRow[] =
    "unparsed_question_numbers" in staging
      ? ((staging as { unparsed_question_numbers?: UnparsedRow[] })
          .unparsed_question_numbers ?? [])
      : [];
  const subjects = [...new Set(records.map((r) => r.question.subject))];

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">TASK-QBANK-002 · PO incelemesi</span>
          <h1>MEB LGS 2022 Sayısal A — aday sorular</h1>
          <p>
            Resmî MEB PDF&apos;inden çıkarılan metin adayları. Bunlar henüz
            yayınlanmış sorular değil: her biri insan kontrolü bekleyen{" "}
            <strong>{staging.status}</strong> durumunda.
          </p>
        </div>
        <Link className="btn btn-primary" href="/calis">
          Çalış ekranı
        </Link>
      </header>

      <section className="card">
        <h2>Kaynak kanıtı</h2>
        <ul>
          <li>
            Kaynak: <code>{records[0].source.source_id}</code> (
            {records[0].source.source_type}, {records[0].source.year})
          </li>
          <li>
            PDF:{" "}
            <a href={records[0].source.pdf_url} rel="noreferrer noopener">
              {records[0].source.pdf_url.split("/").pop()}
            </a>
          </li>
          <li>
            SHA-256: <code>{records[0].source.source_sha256}</code>
          </li>
          <li>Sayfa sayısı: {staging.pages.length}</li>
          <li>Aday sayısı: {staging.candidate_count}</li>
          <li>Yayın durumu: published = {String(staging.published)}</li>
        </ul>
        <p>
          <strong>Gözden geçirme sebepleri:</strong>{" "}
          {review_reasons.join(", ")}
        </p>
        <p>
          <strong>Cevap anahtarı eşlemesi:</strong>{" "}
          {answer_key_summary.mapped_candidates}/{records.length} aday resmî anahtarla
          eşleşti · {answer_key_summary.counts["MATEMATİK"]} Matematik,{" "}
          {answer_key_summary.counts["FEN BİLİMLERİ"]} Fen sorusu.
        </p>
      </section>

      <section className="card">
        <h2>Çıkarılamayan sorular ({unparsed_question_numbers.length})</h2>
        <p>
          Bu soruların numarası sayfada tek başına duruyor; soru metni bir şekil,
          tablo veya grafik içinde. Metin çıkarımı bunları güvenle temsil
          edemediği için aday üretilmedi.
        </p>
        <ul>
          {unparsed_question_numbers.map((row) => (
            <li key={`${row.subject}-${row.question_number}`}>
              {row.subject} — soru {row.question_number} (sayfa {row.page})
            </li>
          ))}
        </ul>
      </section>

      {subjects.map((subject) => {
        const rows = records.filter((r) => r.question.subject === subject);
        return (
          <section className="card" key={subject}>
            <h2>
              {subject} ({rows.length})
            </h2>
            {rows.map((r: Record_) => (
              <article className="pilot-question" key={r.id}>
                <header>
                  <strong>Soru {r.source.question_number}</strong>
                  <span className="tag">
                    sayfa {r.question.page_start}
                    {r.question.page_end !== r.question.page_start
                      ? `–${r.question.page_end}`
                      : ""}
                  </span>
                  <span className="tag tone-bg-warn">
                    {r.extraction.confidence}
                  </span>
                  {r.extraction.warnings.map((w) => (
                    <span className="tag tone-bg-warn" key={w}>
                      {w}
                    </span>
                  ))}
                </header>
                <p className="pilot-stem">{r.question.stem}</p>
                <ul className="pilot-options">
                  {Object.entries(r.question.options).map(([letter, text]) => (
                    <li key={letter}>
                      <b>{letter})</b> {text}
                    </li>
                  ))}
                </ul>
                <footer>
                  <span>
                    Müfredat: {r.curriculum.LGS_REFERENCE_2018_PLUS.status}
                  </span>
                  <span>Çözüm: {r.solution ?? "yok"}</span>
                  <span>Doğrulama: {Object.values(r.checks).filter(Boolean).length}/11</span>
                </footer>
              </article>
            ))}
          </section>
        );
      })}

      <section className="card">
        <h2>Sonraki adım</h2>
        <p>
          Bu adaylar <code>publish_verified.py</code> için hazır değildir. Eksik
          alanlar: müfredat eşlemesi, çözüm açıklaması, doğru cevabın sunucu
          tarafına taşınması ve 11 doğrulama kontrolünün doldurulması.
        </p>
      </section>
    </div>
  );
}
