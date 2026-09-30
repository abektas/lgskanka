import type { Metadata } from "next";
import Link from "next/link";
import { Icon } from "../../components/icons";
import { coachInsights, errorTypes, subjects } from "../../data/content";

export const metadata: Metadata = {
  title: "AI Koç",
  description:
    "Yapay zekâ koçun son cevaplarından çıkardığı teşhisler, önerilen çalışma planı ve H1–H7 hata türlerinin anlamları. Öğrenciyi yargılamadan, hatanın kaynağını bulur.",
  alternates: { canonical: "/ai-koc" },
};

export default function AiKocPage() {
  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">Öğrenme koçu</span>
          <h1>AI Koç</h1>
          <p>
            Koç, son cevaplarındaki hata örüntüsünü inceler ve bir sonraki adımı önerir. Amaç hızlı
            cevap vermek değil; hatanın <strong>kaynağını</strong> bulmak.
          </p>
        </div>
        <Link className="btn btn-primary" href="/calis">
          Teşhis için soru çöz <Icon name="arrow" size={18} />
        </Link>
      </header>

      <section aria-labelledby="teshisler">
        <div className="section-head">
          <h2 id="teshisler">Bugünkü teşhisler</h2>
          <span className="pill is-mint">Son 10 sorunun analizi</span>
        </div>
        <div className="grid-half">
          {coachInsights.map((insight) => {
            const type = errorTypes.find((item) => item.code === insight.code);
            return (
              <article className="card" key={insight.title}>
                <div className="section-head">
                  <h3>
                    <span className="code-tag" style={{ background: type?.color ?? "#6c5ce7" }}>
                      {insight.code}
                    </span>
                    {insight.title}
                  </h3>
                </div>
                <p className="coach-note">{insight.detail}</p>
                {type && (
                  <p className="muted-text" style={{ marginTop: 12, fontSize: 12.5 }}>
                    <strong>Ne yapmalısın:</strong> {type.advice}
                  </p>
                )}
              </article>
            );
          })}
        </div>
      </section>

      <section className="grid-2" aria-label="Önerilen çalışma ve gizlilik">
        <article className="card">
          <div className="section-head">
            <h2>Önerilen çalışma</h2>
          </div>
          <div className="recent-list">
            {subjects.map((subject) => (
              <div className="recent-item" key={subject.slug}>
                <span aria-hidden="true">{subject.icon}</span>
                <span>
                  <strong>{subject.name}</strong> · {subject.topics[0]}
                </span>
                <small>%{subject.score}</small>
              </div>
            ))}
          </div>
          <p className="muted-text" style={{ marginTop: 14, fontSize: 12.5 }}>
            Sıralama hata yoğunluğuna göre yapıldı: en çok hata yaptığın konu en üstte.
          </p>
          <Link className="btn btn-primary btn-block" href="/dersler" style={{ marginTop: 14 }}>
            Konu haritasını aç
          </Link>
        </article>

        <article className="card">
          <h2>Kanıtlarını nasıl kullanıyoruz?</h2>
          <ul className="privacy-list">
            <li>Yazılı açıklaman ve çözüm fotoğrafın yalnızca tek bir analiz isteğinde kullanılır.</li>
            <li>Analiz tamamlandığında ham ses ve görüntü saklanmaz; yalnızca türetilmiş öğrenme verisi tutulur.</li>
            <li>Sonuçlar not olarak kaydedilmez. Koçun amacı gelişimini görmek, seni etiketlemek değil.</li>
            <li>Yanlış cevap &ldquo;başarısızlık&rdquo; değildir; hata türü bilgisi çalışma planını kişiselleştirir.</li>
          </ul>
          <Link className="btn btn-soft btn-block" href="/profil">
            Gizlilik ayarlarını yönet
          </Link>
        </article>
      </section>

      <section className="card" aria-labelledby="hata-turleri">
        <div className="section-head">
          <h2 id="hata-turleri">H1–H7 hata türleri</h2>
          <span className="pill">Koçun ortak dili</span>
        </div>
        <div className="analysis-table">
          {errorTypes.map((error) => (
            <div className="analysis-row" key={error.code}>
              <span>
                <span className="code-tag" style={{ background: error.color }}>
                  {error.code}
                </span>
                {error.name}
              </span>
              <span className="muted-text">{error.definition}</span>
              <em>%{error.share}</em>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
