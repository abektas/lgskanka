import type { Metadata } from "next";
import Link from "next/link";
import { Icon } from "../../components/icons";
import { resources } from "../../data/content";

export const metadata: Metadata = {
  title: "Kaynaklar",
  description:
    "LGS için güvenilir kaynaklar: konu özetleri, MEB örnek soruları, EBA ders videoları, deneme arşivi ve sınav kaygısı rehberi. Koçun önerdiği sırayla çalış.",
  alternates: { canonical: "/kaynaklar" },
};

export default function KaynaklarPage() {
  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">Kütüphane</span>
          <h1>Kaynaklar</h1>
          <p>
            Kaynak çokluğu değil, doğru sıra önemli. Aşağıdaki liste koçun önerdiği sırayla dizildi:
            önce özet, sonra soru, sonra deneme.
          </p>
        </div>
        <Link className="btn btn-primary" href="/dersler">
          Konu haritası <Icon name="arrow" size={18} />
        </Link>
      </header>

      <div className="resource-grid">
        {resources.map((resource) => (
          <article className="resource-card" key={resource.title}>
            <h2>{resource.title}</h2>
            <p>{resource.detail}</p>
            <div className="resource-tags">
              {resource.tags.map((tag) => (
                <span className={`tag tone-bg-${resource.tone}`} key={tag}>
                  {tag}
                </span>
              ))}
            </div>
            {resource.external ? (
              <a className="text-link" href={resource.href} target="_blank" rel="noopener noreferrer">
                Resmî siteye git <Icon name="arrow" size={14} />
              </a>
            ) : (
              <Link className="text-link" href={resource.href}>
                Aç <Icon name="arrow" size={14} />
              </Link>
            )}
          </article>
        ))}
      </div>

      <section className="card" aria-labelledby="kaynak-notu">
        <h2 id="kaynak-notu">Nasıl kullanmalı?</h2>
        <ul className="step-list">
          <li>
            <b>Tek oturumda tek kaynak:</b> aynı anda hem video hem özet açmak dikkat dağınıklığını
            artırır (H7).
          </li>
          <li>
            <b>Özetten sonra hemen 3 soru:</b> pasif okuma yerine hemen hatırlama denemesi, kalıcılığı
            belirgin biçimde artırır.
          </li>
          <li>
            <b>Denemeyi 09:30&apos;da çöz:</b> gerçek sınav saatine benzer bir saatte çözmek, bedeni ve
            dikkati alıştırır.
          </li>
          <li>
            <b>Kaynağı bitirme zorunluluğu yok:</b> işe yaramayan kaynağı bırakmak da planın parçası.
          </li>
        </ul>
      </section>
    </div>
  );
}
