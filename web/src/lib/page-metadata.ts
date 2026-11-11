import type { Metadata } from "next";

// Per-page metadata. layout.tsx owns `title.template` ("%s · Pricekeel"), so
// `title` here is the bare page title and this helper never appends the brand.
// Next applies the template to <title> only, so og:title and twitter:title are
// the bare title too (og:site_name carries the brand).
//
// Next resolves the image urls against metadataBase.
//
// `path` is the route path ("/pricing"); metadataBase in layout.tsx resolves it
// to an absolute canonical and og:url. Setting `openGraph` here replaces the
// root openGraph object, so the shared fields are repeated.
// Shared social image: the root file-convention route (src/app/opengraph-image.tsx,
// 1200x630). A page-level `openGraph` replaces the root one in Next 16, and the
// file-based image is not merged back in, so every page must set the image
// itself. The alt text mirrors `alt` exported by opengraph-image.tsx (a test
// keeps them equal).
export const SOCIAL_IMAGE = {
  url: "/opengraph-image",
  width: 1200,
  height: 630,
  alt: "Pricekeel: we stop AI companies from losing money on heavy users",
} as const;

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
      images: [SOCIAL_IMAGE],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [{ url: SOCIAL_IMAGE.url, alt: SOCIAL_IMAGE.alt }],
    },
  };
  if (noindex) meta.robots = { index: false, follow: false };
  return meta;
}
