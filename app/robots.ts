import type { MetadataRoute } from "next";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // Kişisel çalışma ekranları indekslenmesin; herkese açık içerik sayfaları açık kalsın.
        // TASK-QBANK-007 (C5): pilot inceleme yüzeyleri meta noindex taşır; robots
        // disallow crawl bütçesi + doğrudan URL keşfine karşı savunma derinliğidir.
        disallow: ["/api/", "/profil"],
      },
    ],
    sitemap: `${siteUrl}/sitemap.xml`,
    host: siteUrl,
  };
}
