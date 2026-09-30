import type { Metadata, Viewport } from "next";
import { Baloo_2, Nunito } from "next/font/google";
import "./globals.css";
import { ProfileProvider } from "../components/profile-provider";
import { MobileNav, Sidebar, TopBar } from "../components/chrome";

const bodyFont = Nunito({
  subsets: ["latin", "latin-ext"],
  display: "swap",
  variable: "--font-body",
});

const displayFont = Baloo_2({
  subsets: ["latin", "latin-ext"],
  display: "swap",
  variable: "--font-display",
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "LGS AI Koç — 8. sınıf için kişisel çalışma koçu",
    template: "%s · LGS AI Koç",
  },
  description:
    "LGS AI Koç, 8. sınıf öğrencileri için yapay zekâ destekli çalışma koçudur: günlük görevler, deneme takvimi, H1–H7 hata analizi ve kişiye özel konu tekrarı.",
  keywords: [
    "LGS",
    "LGS hazırlık",
    "8. sınıf",
    "yapay zeka koç",
    "hata analizi",
    "deneme sınavı",
    "konu tekrarı",
    "MEB örnek sorular",
    "matematik",
    "fen bilimleri",
  ],
  applicationName: "LGS AI Koç",
  category: "education",
  authors: [{ name: "LGS AI Koç" }],
  creator: "LGS AI Koç",
  publisher: "LGS AI Koç",
  alternates: { canonical: "/" },
  formatDetection: { telephone: false, address: false, email: false },
  openGraph: {
    type: "website",
    locale: "tr_TR",
    url: "/",
    siteName: "LGS AI Koç",
    title: "LGS AI Koç — 8. sınıf için kişisel çalışma koçu",
    description:
      "Günlük görevler, hata analizi ve kişiye özel tekrar planıyla LGS'ye hazırlan. Yanlışını sadece işaretlemiyoruz, nedenini birlikte buluyoruz.",
    images: [
      {
        url: "/art/hero-boy.webp",
        width: 434,
        height: 536,
        alt: "LGS AI Koç ekranı: çalışma masasındaki öğrenci karakteri",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "LGS AI Koç — 8. sınıf için kişisel çalışma koçu",
    description: "Günlük görevler, H1–H7 hata analizi ve kişiye özel tekrar planı.",
    images: ["/art/hero-boy.webp"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-image-preview": "large", "max-snippet": -1 },
  },
};

export const viewport: Viewport = {
  themeColor: "#6c5ce7",
  width: "device-width",
  initialScale: 1,
  colorScheme: "light",
};

const structuredData = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": `${siteUrl}/#website`,
      url: siteUrl,
      name: "LGS AI Koç",
      inLanguage: "tr-TR",
      description:
        "8. sınıf öğrencileri için yapay zekâ destekli LGS çalışma koçu: görevler, deneme takvimi ve hata analizi.",
      publisher: { "@id": `${siteUrl}/#organization` },
    },
    {
      "@type": "EducationalOrganization",
      "@id": `${siteUrl}/#organization`,
      name: "LGS AI Koç",
      url: siteUrl,
      logo: `${siteUrl}/icon.svg`,
      areaServed: "TR",
    },
    {
      "@type": "SoftwareApplication",
      name: "LGS AI Koç",
      applicationCategory: "EducationalApplication",
      operatingSystem: "Web",
      inLanguage: "tr-TR",
      offers: { "@type": "Offer", price: "0", priceCurrency: "TRY" },
    },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" className={`${bodyFont.variable} ${displayFont.variable}`}>
      <body>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData).replace(/</g, "\\u003c") }}
        />
        <a className="skip-link" href="#icerik">
          İçeriğe geç
        </a>
        <ProfileProvider>
          <div className="shell">
            <Sidebar />
            <div className="main">
              <TopBar />
              <main id="icerik">{children}</main>
            </div>
          </div>
          <MobileNav />
        </ProfileProvider>
      </body>
    </html>
  );
}
