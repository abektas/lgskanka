import type { MetadataRoute } from "next";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

const routes: { path: string; priority: number; changeFrequency: "weekly" | "monthly" }[] = [
  { path: "/", priority: 1, changeFrequency: "weekly" },
  { path: "/calis", priority: 0.9, changeFrequency: "weekly" },
  { path: "/haftalik-test", priority: 0.8, changeFrequency: "weekly" },
  { path: "/sonuclar", priority: 0.8, changeFrequency: "weekly" },
  { path: "/pekistirme", priority: 0.8, changeFrequency: "weekly" },
  { path: "/aylik-denemeler", priority: 0.8, changeFrequency: "weekly" },
  { path: "/kaynaklar", priority: 0.7, changeFrequency: "monthly" },
  { path: "/oduller", priority: 0.6, changeFrequency: "monthly" },
  { path: "/profil", priority: 0.4, changeFrequency: "monthly" },
];

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  return routes.map((route) => ({
    url: `${siteUrl}${route.path}`,
    lastModified,
    changeFrequency: route.changeFrequency,
    priority: route.priority,
  }));
}
