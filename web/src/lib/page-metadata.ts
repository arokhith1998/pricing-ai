import type { Metadata } from "next";

// Per-page metadata. layout.tsx owns `title.template` ("%s · Pricekeel"), so
// `title` here is the bare page title and this helper never appends the brand.
// Next applies the template to <title> only, so og:title and twitter:title are
// the bare title too (og:site_name carries the brand).
//
// `path` is the route path ("/pricing"); metadataBase in layout.tsx resolves it
// to an absolute canonical and og:url. Setting `openGraph` here replaces the
// root openGraph object, so the shared fields are repeated.
export type PageMetadataInput = {
  title: string;
  description: string;
  path: string;
  noindex?: boolean;
};

export function pageMetadata({ title, description, path, noindex }: PageMetadataInput): Metadata {
  if (!path.startsWith("/")) {
    throw new Error(`pageMetadata: path must start with "/", got "${path}"`);
  }
  const meta: Metadata = {
    title,
    description,
    alternates: { canonical: path },
    openGraph: {
      type: "website",
      siteName: "Pricekeel",
      url: path,
      title,
      description,
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
  };
  if (noindex) meta.robots = { index: false, follow: false };
  return meta;
}
