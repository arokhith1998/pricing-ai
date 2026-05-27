import { notFound } from "next/navigation";
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
  return { title: post ? `${post.title} · Pricekeel` : "Pricekeel" };
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
      <a href="/blog" className="text-sm text-teal hover:underline">
        ← Blog
      </a>
      <h1 className="mt-3 text-3xl font-bold leading-tight text-fg">{post.title}</h1>
      <div className="mt-2 text-sm text-muted">
        {fmtDate(post.date)} · {post.author}
      </div>
      <article
        className="pk-prose mt-8"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </main>
  );
}
