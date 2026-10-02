import type { Metadata } from "next";
import Link from "next/link";
import { Icon } from "../../components/icons";
import { errorTypes, subjects } from "../../data/content";
import type { ErrorType } from "../../data/content";

/**
 * Dizi sırasına değil, koda (`"H1"`) göre eşleşir; böylece `errorTypes` sırası
 * değişse de öğrenciye gösterilen kod/ad eşleşmesi bozulmaz.
 */
function errorTypeLabel(code: ErrorType["code"]): string {
  const found = errorTypes.find((item) => item.code === code);
  return found ? `${found.code} · ${found.name.toLowerCase()}` : code;
}

export const metadata: Metadata = {
  title: "Dersler ve konu haritası",
  description:
    "8. sınıf dersleri ve LGS konu haritası: Matematik, Türkçe, Fen Bilimleri ve İngilizce başlıklarında konu listesi, başarı yüzdesi ve kişiselleştirilmiş çalışma önerisi.",
  alternates: { canonical: "/dersler" },
};

const courseLd = {
  "@context": "https://schema.org",
  "@type": "ItemList",
  name: "LGS konu haritası",
  itemListElement: subjects.map((subject, index) => ({
    "@type": "ListItem",
    position: index + 1,
    item: {
      "@type": "Course",
      name: `${subject.name} konu haritası`,
      description: `${subject.name} dersinin LGS konuları: ${subject.topics.join(", ")}.`,
      inLanguage: "tr-TR",
      provider: { "@type": "EducationalOrganization", name: "LGS AI Koç" },
      hasCourseInstance: {
        "@type": "CourseInstance",
        courseMode: "online",
        courseWorkload: "PT15M",
      },
    },
  })),
};

export default function DerslerPage() {
  return (
    <div className="page">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(courseLd).replace(/</g, "\\u003c") }}
      />

      <header className="page-head">
        <div>
          <span className="eyebrow">Konu haritası</span>
          <h1>Dersler</h1>
          <p>
            Her dersin konuları, senin başarı yüzden ve koçun önerdiği sıra. Bir konuya tıkladığında
            kısa özet + pekiştirme soruları açılır.
          </p>
        </div>
        <Link className="btn btn-primary" href="/calis">
          Günün çalışması <Icon name="arrow" size={18} />
        </Link>
      </header>

      {subjects.map((subject) => (
        <section className="card" key={subject.slug} id={subject.slug} aria-labelledby={`${subject.slug}-baslik`}>
          <div className="section-head">
            <h2 id={`${subject.slug}-baslik`}>
              <span className={`subject-ico tone-bg-${subject.tone}`} aria-hidden="true" style={{ display: "inline-grid", marginRight: 10, verticalAlign: "middle" }}>
                {subject.icon}
              </span>
              {subject.name}
            </h2>
            <span className="pill is-mint">
              %{subject.score} · +{subject.delta} puan
            </span>
          </div>

          <div
            className={`bar tone-${subject.tone}`}
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={subject.score}
            aria-label={`${subject.name} başarısı`}
          >
            <i style={{ width: `${subject.score}%` }} />
          </div>

          <ul className="topic-list">
            {subject.topics.map((topic, index) => (
              <li key={topic}>
                <span className="topic-index" aria-hidden="true">
                  {index + 1}
                </span>
                <span>
                  <b>{topic}</b>
                  <small>
                    {index === 0
                      ? "Öncelik: bu konuda son 10 soruda 2 hata var"
                      : "Sıradaki adım: özet sonrası 5 pekiştirme sorusu"}
                  </small>
                </span>
                <Link className="text-link" href="/calis">
                  Çalış <Icon name="arrow" size={14} />
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}

      <section className="cta-band">
        <div>
          <h2>Konularda nerede takıldığını biliyor musun?</h2>
          <p>
            Koçun ortak dili H1–H7 kodlarıdır: her hata türü farklı bir çalışma yöntemi gerektirir.
            Örneğin {errorTypeLabel("H1")} için önce konu özeti,
            {errorTypeLabel("H4")} için daha çok kontrol alışkanlığı gerekir.
          </p>
        </div>
        <Link className="btn" href="/ilerleme">
          Hata dağılımımı gör
        </Link>
      </section>
    </div>
  );
}
