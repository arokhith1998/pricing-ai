// Sitemap for crawlers; robots.txt already points at /sitemap.xml.
// Public static routes plus live blog posts. Gated routes (/diagnostic,
// /guidance, /upload, /competitor-watch) are intentionally excluded: the
// proxy redirects crawlers away from them anyway.
import type { MetadataRoute } from "next";
import { listPosts } from "@/lib/blog";

// Re-evaluated per request so date-scheduled posts join the sitemap the same
// day they go live on /blog (which is also force-dynamic).
export const dynamic = "force-dynamic";

const BASE = "https://www.pricekeel.com";

const STATIC_ROUTES: { path: string; priority: number }[] = [
  { path: "/", priority: 1 },
  { path: "/sample", priority: 0.9 },
  { path: "/calculator", priority: 0.8 },
  { path: "/pricing", priority: 0.8 },
  { path: "/contact", priority: 0.7 },
  { path: "/blog", priority: 0.7 },
  { path: "/privacy", priority: 0.3 },
  { path: "/terms", priority: 0.3 },
  { path: "/trust", priority: 0.5 },
  { path: "/methodology", priority: 0.4 },
  { path: "/subprocessors", priority: 0.3 },
  { path: "/licenses", priority: 0.2 },
];

export default function sitemap(): MetadataRoute.Sitemap {
  const pages: MetadataRoute.Sitemap = STATIC_ROUTES.map(({ path, priority }) => ({
    url: `${BASE}${path}`,
    changeFrequency: "weekly",
    priority,
  }));

  // listPosts() already filters to published posts whose date has arrived,
  // matching the live gating on /blog.
  const posts: MetadataRoute.Sitemap = listPosts().map((p) => ({
    url: `${BASE}/blog/${p.slug}`,
    lastModified: new Date(`${p.date}T00:00:00Z`),
    changeFrequency: "monthly",
    priority: 0.6,
  }));

  return [...pages, ...posts];
}
