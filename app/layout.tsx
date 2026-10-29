import type { Metadata, Viewport } from "next";
import "./globals.css";
import { ProfileProvider } from "../components/profile-provider";
import { MobileNav, Sidebar, TopBar } from "../components/chrome";

// CSS font variables defined in globals.css for offline compatibility

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "LGS KANKA — 8. sınıf için kişisel çalışma arkadaşı",
    template: "%s · LGS KANKA",
  },
  description:
    "LGS KANKA, 8. sınıf öğrencileri için çalışma arkadaşıdır: günlük görevler, deneme takvimi, H1–H7 hata analizi ve kişiye özel konu tekrarı.",
  keywords: [
    "LGS",
    "LGS hazırlık",
    "8. sınıf",
    "LGS deneme takvimi",
    "hata analizi",
    "deneme sınavı",
    "konu tekrarı",
    "MEB örnek sorular",
    "matematik",
    "fen bilimleri",
  ],
  applicationName: "LGS KANKA",
  category: "education",
  authors: [{ name: "LGS KANKA" }],
  creator: "LGS KANKA",
  publisher: "LGS KANKA",
  alternates: { canonical: "/" },
  formatDetection: { telephone: false, address: false, email: false },
  openGraph: {
    type: "website",
    locale: "tr_TR",
    url: "/",
    siteName: "LGS KANKA",
    title: "LGS KANKA — 8. sınıf için kişisel çalışma arkadaşı",
    description:
      "Günlük görevler, hata analizi ve kişiye özel tekrar planıyla LGS'ye hazırlan. Yanlışını sadece işaretlemiyoruz, nedenini birlikte buluyoruz.",
    images: [
      {
        url: "/art/hero-boy.webp",
        width: 434,
        height: 536,
        alt: "LGS KANKA ekranı: çalışma masasındaki öğrenci karakteri",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "LGS KANKA — 8. sınıf için kişisel çalışma arkadaşı",
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
      name: "LGS KANKA",
      inLanguage: "tr-TR",
      description:
        "8. sınıf öğrencileri için LGS çalışma arkadaşı: görevler, deneme takvimi ve hata analizi.",
      publisher: { "@id": `${siteUrl}/#organization` },
    },
    {
      "@type": "EducationalOrganization",
      "@id": `${siteUrl}/#organization`,
      name: "LGS KANKA",
      url: siteUrl,
      logo: `${siteUrl}/icon.svg`,
      areaServed: "TR",
    },
    {
      "@type": "SoftwareApplication",
      name: "LGS KANKA",
      applicationCategory: "EducationalApplication",
      operatingSystem: "Web",
      inLanguage: "tr-TR",
      offers: { "@type": "Offer", price: "0", priceCurrency: "TRY" },
    },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" className="font-loaded">
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
