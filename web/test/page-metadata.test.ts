import { describe, expect, it } from "vitest";

import { readFileSync } from "node:fs";
import { pageMetadata, SOCIAL_IMAGE } from "@/lib/page-metadata";

const input = {
  title: "Pricing",
  description: "How Pricekeel is sold and what an engagement includes, scoped by deal volume.",
  path: "/pricing",
};

describe("pageMetadata", () => {
  it("returns the bare title and never appends the brand suffix", () => {
    const m = pageMetadata(input);
    expect(m.title).toBe("Pricing");
    expect(JSON.stringify(m)).not.toContain("Pricekeel ·");
    expect(JSON.stringify(m)).not.toContain(" · Pricekeel");
  });

  it("sets the canonical, og:url, og:title and the twitter block", () => {
    const m = pageMetadata(input);
    expect(m.alternates?.canonical).toBe("/pricing");
    expect(m.openGraph?.url).toBe("/pricing");
    expect(m.openGraph?.title).toBe("Pricing");
    expect(m.openGraph?.description).toBe(input.description);
    expect(m.twitter).toMatchObject({
      card: "summary_large_image",
      title: "Pricing",
      description: input.description,
    });
    expect(m.description).toBe(input.description);
  });

  it("keeps the shared og fields the root layout sets", () => {
    const og = pageMetadata(input).openGraph as { type?: string; siteName?: string };
    expect(og.type).toBe("website");
    expect(og.siteName).toBe("Pricekeel");
  });

  it("is indexable by default and noindex,nofollow when asked", () => {
    expect(pageMetadata(input).robots).toBeUndefined();
    expect(pageMetadata({ ...input, noindex: true }).robots).toEqual({ index: false, follow: false });
  });

  it("rejects a path without a leading slash", () => {
    expect(() => pageMetadata({ ...input, path: "pricing" })).toThrow(/must start with/);
  });

  it("supports the root path", () => {
    expect(pageMetadata({ ...input, path: "/" }).alternates?.canonical).toBe("/");
  });

  it("sets openGraph.images and twitter.images to the root /opengraph-image (1200x630)", () => {
    const m = pageMetadata(input);
    expect(m.openGraph?.images).toEqual([SOCIAL_IMAGE]);
    expect(m.twitter?.images).toEqual([SOCIAL_IMAGE.url]);
    expect(SOCIAL_IMAGE).toMatchObject({ url: "/opengraph-image", width: 1200, height: 630 });
    expect(SOCIAL_IMAGE.alt.length).toBeGreaterThan(10);
  });

  it("keeps the image alt equal to the alt exported by opengraph-image.tsx", () => {
    const src = readFileSync("src/app/opengraph-image.tsx", "utf8");
    const alt = src.match(/export const alt =\s*"([^"]+)"/)?.[1];
    expect(alt).toBe(SOCIAL_IMAGE.alt);
    expect(src).toMatch(/size = \{ width: 1200, height: 630 \}/);
  });

  it("keeps the image on noindex pages too", () => {
    expect(pageMetadata({ ...input, noindex: true }).openGraph?.images).toEqual([SOCIAL_IMAGE]);
  });
});
