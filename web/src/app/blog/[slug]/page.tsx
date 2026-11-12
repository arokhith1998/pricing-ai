import { notFound } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";
import { getPost, renderMarkdown } from "@/lib/blog";
import { fmtDate } from "@/lib/format";
import { Button } from "@/components/ui";
import { BOOKING_LABEL, BOOKING_URL } from "@/lib/site-nav";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = getPost(slug);
  if (!post) return { title: "Post not found", robots: { index: false } };
  // The root layout's title template appends "· Pricekeel".
  return {
    title: post.title,
    description: post.excerpt,
    alternates: { canonical: `/blog/${post.slug}` },
    // PK-116 (F17): posts are unlinked and noindexed.
    robots: { index: false },
    openGraph: {
      type: "article",
      url: `/blog/${post.slug}`,
      title: post.title,
      description: post.excerpt,
      publishedTime: `${post.date}T00:00:00Z`,
      authors: [post.author],
      siteName: "Pricekeel",
    },
    twitter: {
      card: "summary_large_image",
      title: post.title,
      description: post.excerpt,
    },
  };
}

export default async function PostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = getPost(slug);
  if (!post) notFound();

  const html = renderMarkdown(post.body);
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Link href="/blog" className="text-sm text-teal hover:underline">
        ← Blog
      </Link>
      <h1 className="mt-3 text-3xl font-bold leading-tight text-fg">{post.title}</h1>
      <div className="mt-2 text-sm text-muted">
        {fmtDate(post.date)} · {post.author}
      </div>
      <article
        className="pk-prose mt-8"
        dangerouslySetInnerHTML={{ __html: html }}
      />

      <section className="mt-12 rounded-2xl border border-teal/40 bg-surface px-6 py-8 text-center">
        <h2 className="text-xl font-bold text-fg">
          Twenty minutes on how you price per unit.
        </h2>
        <div className="mt-5 flex justify-center">
          <Button href={BOOKING_URL}>{BOOKING_LABEL}</Button>
        </div>
      </section>
    </main>
  );
}
