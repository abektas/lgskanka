"use client";

import { useProfile } from "./profile-provider";
import { LoginScreen } from "./login-screen";

const structuredData = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": `${typeof window !== "undefined" ? window.location.origin : "http://localhost:3000"}/#website`,
      url: typeof window !== "undefined" ? window.location.origin : "http://localhost:3000",
      name: "LGS KANKA",
      inLanguage: "tr-TR",
      description:
        "8. sınıf öğrencileri için LGS çalışma arkadaşı: görevler, deneme takvimi ve hata analizi.",
      publisher: { "@id": `${typeof window !== "undefined" ? window.location.origin : "http://localhost:3000"}/#organization` },
    },
    {
      "@type": "EducationalOrganization",
      "@id": `${typeof window !== "undefined" ? window.location.origin : "http://localhost:3000"}/#organization`,
      name: "LGS KANKA",
      url: typeof window !== "undefined" ? window.location.origin : "http://localhost:3000",
      logo: `${typeof window !== "undefined" ? window.location.origin : "http://localhost:3000"}/icon.svg`,
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

export function ProfileGate({ children }: { children: React.ReactNode }) {
  const { ready, needsProfileSelection, activeProfile } = useProfile();

  // Öğretmen paneli öğrenci girişi istemez — kendi anahtarıyla açılır.
  const isTeacherPage =
    typeof window !== "undefined" && window.location.pathname.startsWith("/ogretmen");
  if (isTeacherPage) {
    return <>{children}</>;
  }

  if (!ready) {
    return (
      <div style={{ display: "grid", placeItems: "center", minHeight: "100vh", background: "var(--zemin)" }}>
        <div className="spinner" />
      </div>
    );
  }

  if (needsProfileSelection || !activeProfile) {
    return (
      <>
        <LoginScreen />
      </>
    );
  }

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(structuredData).replace(/</g, "\\u003c"),
        }}
      />
      <a className="skip-link" href="#icerik">
        İçeriğe geç
      </a>
      {children}
    </>
  );
}