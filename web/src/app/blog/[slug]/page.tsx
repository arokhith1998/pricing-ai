import { notFound } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";
import { getPost, renderMarkdown } from "@/lib/blog";
import { fmtDate } from "@/lib/format";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = getPost(slug);
  if (!post) return { title: "Post not found" };
  // The root layout's title template appends "· Pricekeel".
  return {
    title: post.title,
    description: post.excerpt,
    alternates: { canonical: `/blog/${post.slug}` },
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
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal">
          See it on real numbers
        </p>
        <h2 className="mt-2 text-xl font-bold text-fg">
          This is the same math the diagnostic runs on your own book.
        </h2>
        <div className="mt-5 flex flex-wrap justify-center gap-3">
          <Link
            href="/sample"
            className="rounded-lg bg-teal px-5 py-3 font-semibold text-bg transition hover:-translate-y-0.5 hover:bg-teal/90"
          >
            Explore a live sample
          </Link>
          <Link
            href="/contact"
            className="rounded-lg border border-mist bg-surface-2 px-5 py-3 font-medium text-fg transition hover:border-teal"
          >
            Bring one real discount exception
          </Link>
        </div>
      </section>
    </main>
  );
}
