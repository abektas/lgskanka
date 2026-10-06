import type { Metadata } from "next";
import Link from "next/link";
import pilot from "../../scripts/source-ingestion/data/questions/pilot-2022-visual/pilot.json";

export const metadata: Metadata = {
  title: "2022 Görsel Soru Pilotu",
  robots: { index: false, follow: false },
};

type Record_ = (typeof pilot.records)[number];

const AFFECTED = [4, 10, 11, 12, 14, 19];

/**
 * TASK-QBANK-003 pilot ekranı.
 *
 * Amaç: pypdf metin çıkarımının temsil edemediği altı Matematik sorusunun
 * (Q4/Q10/Q11/Q12/Q14/Q19) resmî MEB PDF'den kırpılmış görselini PO'ya
 * inceletme imkânı vermek; ayrıca metin-çıkarılabilen iki kontrol sorusuyla
 * "yapılandırılmış metin ne zaman yeterli" sınırını göstermek.
 *
 * Yayın yüzeyi DEĞİLDİR: tüm kayıtlar NEEDS_REVIEW/published=false, resmî
 * cevap anahtarı hiçbir payload'a yazılmaz, pypdf/MinerU metinleri
 * "debug, resmî değildir" etiketiyle gösterilir.
 */
export default function Pilot2022VisualPage() {
  const { records, source, tooling } = pilot;
  const imageBacked = records.filter((r: Record_) => r.mode === "image");
  const controls = records.filter((r: Record_) => r.mode === "control");

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">TASK-QBANK-003 · teknik pilot</span>
          <h1>MEB LGS 2022 Sayısal A — görsel soru temsili</h1>
          <p className="pv-lead">
            pypdf metin çıkarımının bozduğu {imageBacked.length} soru için resmî
            PDF sayfasından 300 DPI kırpma üretildi. Bu bir pilot çalışmasıdır:
            kalıcı şema kararı değildir, hiçbir soru yayınlanmamıştır.
          </p>
        </div>
        <Link className="btn btn-primary" href="/pilot-2022">
          Metin pilotu (QBank-002)
        </Link>
      </header>

      <section className="card">
        <h2>Kaynak kanıtı</h2>
        <ul className="pv-list">
          <li>
            Kaynak: <code>{source.source_id}</code> ({source.source_type},{" "}
            {source.year})
          </li>
          <li>
            PDF:{" "}
            <a href={source.pdf_url} rel="noreferrer noopener">
              {source.pdf_url.split("/").pop()}
            </a>
          </li>
          <li>
            SHA-256: <code>{source.sha256}</code>
          </li>
          <li>
            Kırpma: {tooling.render_tool} {tooling.render_tool_version} ·{" "}
            {tooling.render_dpi} DPI · bölge bulma{" "}
            <code>{records[0].extraction.region_detection}</code>
          </li>
          <li>
            Metin tabanı: {tooling.baseline_tool} · düzen karşılaştırması:{" "}
            {tooling.layout_tool}
          </li>
          <li>
            Durum: <code>{pilot.status}</code> · published ={" "}
            {String(pilot.published)}
          </li>
        </ul>
<section className="card">
        <h2>
          Etkilenen sorular — görsel temsil ({imageBacked.length}/
          {AFFECTED.length})
        </h2>
        <p className="pv-reason">
          Aşağıdaki her kayıt resmî sayfanın birebir raster kırpmasıdır; metin
          OCR ile yeniden kurulmamıştır (
          <code>reconstructed_from_ocr=false</code>).
        </p>
        {imageBacked.map((r: Record_) => (
          <article className="pv-item" key={r.id}>
            <div className="pv-item-head">
              <strong>Soru {r.question.question_number}</strong>
              <span className="tag">{r.question.subject}</span>
              <span className="tag">sayfa {r.question.page}</span>
              <span className="tag tone-bg-mavi">{r.question.representation}</span>
              <span className="tag">
                {r.image.pixel_width}×{r.image.pixel_height} px
              </span>
              <span className="tag">{r.status}</span>
              <span className="tag">published={String(r.published)}</span>
            </div>
            <figure className="pv-figure">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={r.image.public_path}
                alt={`MEB 2022 Sayısal A Matematik soru ${r.question.question_number} — resmî sayfa ${r.question.page} kırpması`}
                width={r.image.pixel_width}
                height={r.image.pixel_height}
              />
              <figcaption>
                Kırpma (pt): x0={r.image.clip_rect_pt.x0.toFixed(1)} y0=
                {r.image.clip_rect_pt.y0.toFixed(1)} x1=
                {r.image.clip_rect_pt.x1.toFixed(1)} y1=
                {r.image.clip_rect_pt.y1.toFixed(1)} · sayfa vektör çizimi:{" "}
                {r.extraction.page_vector_drawings} · gömülü raster:{" "}
                {r.extraction.page_embedded_images}
              </figcaption>
            </figure>
            <p className="pv-reason">
              <strong>Neden görsel:</strong> {r.reason}
            </p>
            <div className="pv-cols">
              <div className="pv-block">
                <h4>Çıkarım durumu</h4>
                <ul>
                  <li>
                    Araç: {r.extraction.tool} {r.extraction.tool_version} · yöntem:{" "}
                    {r.extraction.method}
                  </li>
                  <li>
                    pypdf soru bloğu üretti mi:{" "}
                    {String(r.baseline.produced_question_block)}
                  </li>
                  <li>
                    Yapılandırılmış metin:{" "}
                    {r.structured_text ? "var (kontrol)" : "yok"}
                  </li>
                </ul>
              </div>
              <div className="pv-block">
                <h4>Kaynak</h4>
                <ul>
                  <li>
                    Kitapçık: {r.source.booklet} · PDF sayfası: {r.question.page}
                  </li>
                  <li>
                    SHA-256: <code>{r.source.source_sha256}</code>
                  </li>
                  <li>
                    Arşiv: <code>{r.source.archive_path}</code>
                  </li>
                </ul>
              </div>
              <div className="pv-block pv-debug">
                <h4>pypdf metni — debug, resmî değildir</h4>
                <pre>{r.baseline.page_text_excerpt}</pre>
              </div>
              <div className="pv-block pv-debug">
                <h4>MinerU (flash tier) — debug, resmî değildir</h4>
                {r.mineru_comparison ? (
                  <>
                    <p>
                      Blok türleri:{" "}
                      {JSON.stringify(r.mineru_comparison.block_types)}
                    </p>
                    <pre>
                      {r.mineru_comparison.text_excerpt || "(metin yok)"}
                    </pre>
                  </>
                ) : (
                  <p>MinerU çıktısı yok.</p>
                )}
              </div>
            </div>
          </article>
        ))}
      </section>
      </section>
<section className="card">
        <h2>Kontrol soruları — yapılandırılmış metin yolu ({controls.length})</h2>
        <p className="pv-reason">
          Bu sorularda pypdf soru bloğunu eksiksiz üretti; görsel gerekmedi. Aynı
          zamanda kırpma da üretildi ki PO, metin ile görseli yan yana
          karşılaştırabilsin.
        </p>
        {controls.map((r: Record_) => (
          <article className="pv-item" key={r.id}>
            <div className="pv-item-head">
              <strong>Soru {r.question.question_number}</strong>
              <span className="tag">{r.question.subject}</span>
              <span className="tag">sayfa {r.question.page}</span>
              <span className="tag tone-bg-mint">{r.question.representation}</span>
              <span className="tag">{r.status}</span>
              <span className="tag">published={String(r.published)}</span>
            </div>
            <figure className="pv-figure">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={r.image.public_path}
                alt={`MEB 2022 Sayısal A Matematik soru ${r.question.question_number} — resmî sayfa ${r.question.page} kırpması`}
                width={r.image.pixel_width}
                height={r.image.pixel_height}
              />
              <figcaption>Karşılaştırma için resmî sayfa kırpması.</figcaption>
            </figure>
            <p className="pv-reason">
              <strong>Neden metin:</strong> {r.reason}
            </p>
            <div className="pv-cols">
              <div className="pv-block">
                <h4>pypdf metni (yapılandırılmış, resmî değil)</h4>
                <p>{r.structured_text?.stem}</p>
                <ul>
                  {Object.entries(r.structured_text?.options ?? {}).map(
                    ([letter, text]) => (
                      <li key={letter}>
                        <b>{letter})</b> {text}
                      </li>
                    ),
                  )}
                </ul>
              </div>
              <div className="pv-block pv-debug">
                <h4>Karşılaştırma notu</h4>
                <ul>
                  <li>
                    pypdf soru bloğu üretti mi:{" "}
                    {String(r.baseline.produced_question_block)}
                  </li>
                  <li>
                    MinerU blok türleri:{" "}
                    {r.mineru_comparison
                      ? JSON.stringify(r.mineru_comparison.block_types)
                      : "yok"}
                  </li>
                </ul>
              </div>
            </div>
          </article>
        ))}
      </section>

      <section className="card">
        <h2>Teknik sonuç (pilot gözlemi)</h2>
        <ul className="pv-conclusion">
          <li>
            <strong>MinerU (flash tier):</strong> blok türlerini ayırdı
            (text/image/equation/table), ancak metni OCR düzleştirmesiyle verdi:
            Q4 ve Q12&apos;de denklemler <code>a2 + c2 = b2</code>, Q19&apos;da{" "}
            <code>pr 2</code> biçiminde bozuldu. Yerel kurulumda resmî
            layout/table modelleri bulunmadığı için MinerU bu ortamda metin
            tabanı olarak kullanılamadı; yalnızca karşılaştırma olarak tutuldu.
          </li>
          <li>
            <strong>PyMuPDF:</strong> resmî sayfayı 300 DPI raster olarak kırptı;
            şekil, tablo ve denklemleri yeniden kurulum olmadan korudu. Pilotun
            görsel temsil yolu bu nedenle PyMuPDF&apos;dir.
          </li>
          <li>
            <strong>pypdf:</strong> altı soruda soru numarası ile gövde arasındaki
            yapıyı kaybetti (Q4, Q10, Q11, Q12, Q14, Q19); Q14&apos;te takvim
            tablosunun hücre ilişkileri, Q19&apos;da ölçü etiketleri dağıtıldı.
          </li>
          <li>
            <strong>Öneri (pilot kanıtına dayalı):</strong> kalıcı model{" "}
            <em>hibrit</em> olmalı — metin-çıkarılabilir sorular yapılandırılmış
            metin, görsel/tablo/denklem içeren sorular resmî sayfa kırpması
            (image-backed). Bu bir ürün politikası kararı değildir; PO onayı
            gerekir.
          </li>
          <li>
            <strong>Kısıtlar:</strong> bölge bulma metin bloklarına dayanır; tamamen
            görsel soru numarası yoksa bölge bulunamaz (bu pilotta gerekmedi).
            PNG kırpma dosya boyutunu artırır. Görsel doğruluk için insan kontrolü
            gerekir. Hiçbir kayıt VERIFIED değildir, cevap anahtarı istemciye
            gönderilmez.
          </li>
        </ul>
      </section>
    </div>
  );
}