// Sitemap for crawlers; robots.txt already points at /sitemap.xml.
// PK-116 (F17): only the pages linked from the site. The unlinked routes
// (/calculator, /sample, /blog and posts, /methodology, /crm, /upload) are
// noindexed and stay out, and /pricing is a redirect to /audit.
import type { MetadataRoute } from "next";

const BASE = "https://www.pricekeel.com";

export const SITEMAP_PATHS: { path: string; priority: number }[] = [
  { path: "/", priority: 1 },
  { path: "/audit", priority: 0.9 },
  { path: "/contact", priority: 0.7 },
  { path: "/trust", priority: 0.5 },
  { path: "/privacy", priority: 0.3 },
  { path: "/terms", priority: 0.3 },
];

export default function sitemap(): MetadataRoute.Sitemap {
  return SITEMAP_PATHS.map(({ path, priority }) => ({
    url: `${BASE}${path}`,
    changeFrequency: "weekly",
    priority,
  }));
}
