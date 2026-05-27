import Link from "next/link";
import type { Metadata } from "next";
import { listPosts } from "@/lib/blog";
import { fmtDate } from "@/lib/format";
import Reveal from "@/components/Reveal";

// Re-evaluated per request so date-scheduled posts appear once their day arrives.
export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Blog · Pricekeel" };

export default function BlogIndex() {
  const posts = listPosts();
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Reveal>
        <h1 className="text-3xl font-bold text-fg">Blog</h1>
        <p className="mt-1 text-muted">
          Notes on pricing, discounting, and margin for usage-based B2B SaaS.
        </p>
      </Reveal>

      {posts.length === 0 ? (
        <p className="mt-8 text-muted">No posts yet. Check back soon.</p>
      ) : (
        <div className="mt-8 space-y-4">
          {posts.map((p, i) => (
            <Reveal key={p.slug} delay={0.04 * i}>
              <Link
                href={`/blog/${p.slug}`}
                className="block rounded-xl border border-mist bg-surface p-5 transition hover:-translate-y-0.5 hover:border-teal"
              >
                <div className="text-xs text-muted">
                  {fmtDate(p.date)} · {p.author}
                </div>
                <h2 className="mt-1 text-lg font-semibold text-fg">{p.title}</h2>
                <p className="mt-1 text-sm text-muted">{p.excerpt}</p>
              </Link>
            </Reveal>
          ))}
        </div>
      )}
    </main>
  );
}
