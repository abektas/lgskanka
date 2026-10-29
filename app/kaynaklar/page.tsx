import type { Metadata } from "next";
import Link from "next/link";
import { Icon } from "../../components/icons";
import { resources } from "../../data/content";

export const metadata: Metadata = {
  title: "Kaynaklar",
  description:
    "LGS için güvenilir kaynaklar: konu özetleri, MEB örnek soruları, EBA ders videoları, deneme arşivi ve sınav kaygısı rehberi. Kankanın önerdiği sırayla çalış.",
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
            EBA konu anlatımları, YouTube kanalları, MEB örnek sorular ve sınav kaygısı rehberi — ihtiyacına göre seç, çalış.
            önce özet, sonra soru, sonra deneme.
          </p>
        </div>

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
            {resource.links && resource.links.length > 0 ? (
              <div className="resource-links">
                {resource.links.map((link) => (
                  <a key={link.url} className="text-link" href={link.url} target="_blank" rel="noopener noreferrer">
                    {link.label}
                  </a>
                ))}
              </div>
            ) : resource.external ? (
              <a className="text-link" href={resource.href} target="_blank" rel="noopener noreferrer">
                Resmî siteye git <Icon name="arrow" size={14} />
              </a>
            ) : (
              <Link
                className="text-link"
                href={resource.href}
                target={resource.newTab ? "_blank" : undefined}
                rel={resource.newTab ? "noopener noreferrer" : undefined}
              >
                Aç <Icon name="arrow" size={14} />
              </Link>
            )}
          </article>
        ))}
      </div>

    </div>
  );
}
