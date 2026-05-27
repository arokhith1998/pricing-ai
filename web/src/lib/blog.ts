// Markdown blog read from web/content/blog/*.md (server-only). Posts are
// "scheduled" simply by their `date`: a post goes live once its date arrives,
// so a future-dated file sits in the repo until then. See web/content/CONTENT.md.
import fs from "node:fs";
import path from "node:path";
import { marked } from "marked";

const DIR = path.join(process.cwd(), "content", "blog");

export type Post = {
  slug: string;
  title: string;
  date: string; // YYYY-MM-DD
  author: string;
  excerpt: string;
  published: boolean;
  body: string;
};

function parse(file: string, raw: string): Post {
  const m = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/.exec(raw);
  const fm: Record<string, string> = {};
  let body = raw;
  if (m) {
    body = m[2];
    for (const line of m[1].split(/\r?\n/)) {
      const idx = line.indexOf(":");
      if (idx === -1) continue;
      fm[line.slice(0, idx).trim()] = line
        .slice(idx + 1)
        .trim()
        .replace(/^["']|["']$/g, "");
    }
  }
  return {
    slug: file.replace(/\.md$/, ""),
    title: fm.title ?? file,
    date: fm.date ?? "1970-01-01",
    author: fm.author ?? "Pricekeel",
    excerpt: fm.excerpt ?? "",
    published: fm.published !== "false",
    body,
  };
}

function all(): Post[] {
  if (!fs.existsSync(DIR)) return [];
  return fs
    .readdirSync(DIR)
    .filter((f) => f.endsWith(".md"))
    .map((f) => parse(f, fs.readFileSync(path.join(DIR, f), "utf8")))
    .sort((a, b) => b.date.localeCompare(a.date));
}

function isLive(p: Post): boolean {
  const today = new Date().toISOString().slice(0, 10);
  return p.published && p.date <= today;
}

export function listPosts(): Post[] {
  return all().filter(isLive);
}

export function getPost(slug: string): Post | null {
  const p = all().find((x) => x.slug === slug);
  return p && isLive(p) ? p : null;
}

export function renderMarkdown(md: string): string {
  return marked.parse(md, { async: false }) as string;
}
