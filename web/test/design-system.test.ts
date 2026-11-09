import { createElement as h } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import {
  Artifact,
  Button,
  Card,
  DataTable,
  Eyebrow,
  PageHeader,
  Section,
  Stat,
  StatusIcons,
  StatusPill,
  SyntheticTag,
  SYNTHETIC_LABELS,
  BUTTON_VARIANTS,
} from "@/components/ui";

// WCAG 2.x relative luminance and contrast ratio.
function luminance(hex: string) {
  const c = [1, 3, 5]
    .map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
function contrast(a: string, b: string) {
  const [x, y] = [luminance(a), luminance(b)];
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}

const css = readFileSync(new URL("../src/app/globals.css", import.meta.url), "utf8");
function token(name: string) {
  const m = css.match(new RegExp(`--color-${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!m) throw new Error(`token ${name} missing`);
  return m[1];
}

describe("palette tokens are unchanged", () => {
  it("keeps the dark-theme hex values from brand/PALETTE.md", () => {
    expect(token("bg")).toBe("#0a0f1a");
    expect(token("surface")).toBe("#111a2b");
    expect(token("surface-2")).toBe("#0d1422");
    expect(token("border")).toBe("#1f2c43");
    expect(token("fg")).toBe("#e9f0f8");
    expect(token("muted")).toBe("#8ea3bd");
    expect(token("teal")).toBe("#2dd4bf");
    expect(token("coral")).toBe("#ff6b54");
    expect(token("green")).toBe("#34d399");
    expect(token("amber")).toBe("#f0b34a");
    expect(token("navy")).toBe("#0d9488");
  });
  it("defines the type scale, spacing steps and surfaces", () => {
    for (const t of ["display", "h1", "h2", "h3", "lead", "body", "small", "eyebrow", "micro"]) {
      expect(css).toContain(`--text-${t}:`);
    }
    for (const s of ["section-sm", "section-md", "section-lg", "gutter", "gutter-lg"]) {
      expect(css).toContain(`--spacing-${s}:`);
    }
    for (const c of [".pk-surface-card", ".pk-surface-inset", ".pk-surface-artifact", ".pk-band"]) {
      expect(css).toContain(c);
    }
  });
});

describe("contrast", () => {
  it("primary button text-bg on bg-teal is at least 10:1 (10.29:1)", () => {
    expect(BUTTON_VARIANTS.primary).toContain("bg-teal");
    expect(BUTTON_VARIANTS.primary).toContain("text-bg");
    const ratio = contrast(token("bg"), token("teal"));
    expect(ratio).toBeGreaterThanOrEqual(10);
    expect(ratio).toBeCloseTo(10.29, 1);
  });
  it("white on the legacy #0D9488 action fill is 3.74:1 (why it is retired)", () => {
    expect(contrast("#ffffff", token("navy"))).toBeCloseTo(3.74, 1);
  });
  it("control border Slate #5B6B7B is at least 3:1 on both inset and card", () => {
    expect(css).toMatch(/--color-control:\s*#5b6b7b/i);
    expect(contrast("#5B6B7B", "#0D1422")).toBeGreaterThanOrEqual(3);
    expect(contrast("#5B6B7B", "#111A2B")).toBeGreaterThanOrEqual(3);
  });
  it("the decorative hairline fails 3:1, so controls must not use it", () => {
    expect(contrast(token("border"), token("surface"))).toBeLessThan(3);
  });
  it("body muted text passes AA on canvas and card", () => {
    expect(contrast(token("muted"), token("bg"))).toBeGreaterThanOrEqual(4.5);
    expect(contrast(token("muted"), token("surface"))).toBeGreaterThanOrEqual(4.5);
  });
});

// Render a component to static markup with its props type-checked.
function html<P>(C: (props: P) => unknown, props: P): string {
  return renderToStaticMarkup(h(C as never, props as never));
}

describe("ui primitives render", () => {
  it("Section renders a band, a width container and children", () => {
    const out = html(Section, {
      band: "band",
      width: "prose",
      id: "x",
      children: h("p", null, "inside"),
    });
    expect(out).toContain("<section");
    expect(out).toContain('data-band="band"');
    expect(out).toContain("pk-band");
    expect(out).toContain("max-w-prose-page");
    expect(out).toContain("inside");
  });

  it("PageHeader renders exactly one h1, with eyebrow and lead", () => {
    const out = html(PageHeader, { title: "Title", eyebrow: "Eyebrow", lead: "Lead copy" });
    expect(out.match(/<h1/g)).toHaveLength(1);
    expect(out).toContain("Title");
    expect(out).toContain("pk-eyebrow");
    expect(out).toContain("pk-lead");
  });

  it("Card renders card and inset tones, interactive hover class", () => {
    const card = html(Card, { interactive: true, children: "c" });
    expect(card).toContain("pk-surface-card");
    expect(card).toContain("pk-surface-interactive");
    expect(html(Card, { tone: "inset", children: "c" })).toContain("pk-surface-inset");
    expect(card).not.toMatch(/rotate|3d/);
  });

  it("Artifact renders the artifact surface with an accessible name and caption", () => {
    const out = html(Artifact, {
      label: "Decision record",
      caption: "Synthetic sample deal.",
      children: "body",
    });
    expect(out).toContain("<figure");
    expect(out).toContain('aria-label="Decision record"');
    expect(out).toContain("pk-surface-artifact");
    expect(out).toContain("Synthetic sample deal.");
  });

  it("Button renders primary as bg-teal with text-bg, as link and as button", () => {
    const link = html(Button, { href: "/contact", children: "Talk to us" });
    expect(link).toContain('href="/contact"');
    expect(link).toContain("bg-teal");
    expect(link).toContain("text-bg");
    expect(link).not.toContain("text-white");
    expect(link).toContain("min-h-11");
    const btn = html(Button, { variant: "secondary", type: "submit", children: "Go" });
    expect(btn).toContain("<button");
    expect(btn).toContain('type="submit"');
    expect(btn).toContain("border-control");
    expect(html(Button, { href: "mailto:a@b.co", children: "m" })).toContain("<a ");
  });

  it("StatusPill renders both the label and an icon", () => {
    const out = html(StatusPill, { tone: "leak", label: "Gap to win point", icon: StatusIcons.leak });
    expect(out).toContain("Gap to win point");
    expect(out).toContain("<svg");
    expect(out).toContain("text-coral");
  });

  it("StatusPill cannot render without a label or an icon", () => {
    // @ts-expect-error icon is required
    expect(html(StatusPill, { tone: "ok", label: "Within policy" })).toBe("");
    expect(html(StatusPill, { tone: "ok", label: "  ", icon: StatusIcons.ok })).toBe("");
    // @ts-expect-error label is required
    expect(html(StatusPill, { tone: "ok", icon: StatusIcons.ok })).toBe("");
  });

  it("Stat renders the SyntheticTag itself when source is sample", () => {
    const out = html(Stat, { label: "Gap to win point", value: "$8.9M", source: "sample" });
    expect(out).toContain("Gap to win point");
    expect(out).toContain(SYNTHETIC_LABELS.sample);
    const ill = html(Stat, { label: "x", value: "1", source: "sample", syntheticVariant: "illustrative" });
    expect(ill).toContain(SYNTHETIC_LABELS.illustrative);
  });

  it("Stat with reader input has no synthetic tag, and source is mandatory", () => {
    const out = html(Stat, { label: "Your leakage", value: "$1.2M", source: "input" });
    expect(out).not.toContain("Synthetic");
    // @ts-expect-error source is required
    html(Stat, { label: "x", value: "1" });
    // @ts-expect-error a reader-input stat cannot carry a synthetic variant
    html(Stat, { label: "x", value: "1", source: "input", syntheticVariant: "sample" });
  });

  it("Eyebrow renders the teal label class", () => {
    expect(html(Eyebrow, { children: "Label" })).toContain("pk-eyebrow");
  });

  it("SyntheticTag renders neutral text with no status color", () => {
    const out = html(SyntheticTag, {});
    expect(out).toContain("Synthetic sample");
    expect(out).not.toMatch(/coral|green|amber/);
  });

  it("DataTable renders a captioned region, header cells, a row header and numeric alignment", () => {
    type Row = { band: string; rate: string };
    const out = renderToStaticMarkup(
      h(DataTable<Row>, {
        caption: "Win rate by band",
        columns: [
          { key: "band", header: "Band" },
          { key: "rate", header: "Win rate", numeric: true },
        ],
        rows: [{ band: "5 to 10%", rate: "68%" }],
      }),
    );
    expect(out).toContain('aria-label="Win rate by band"');
    expect(out).toContain("<caption");
    expect(out).toContain('scope="col"');
    expect(out).toContain('scope="row"');
    expect(out).toContain("text-right");
    expect(out).toContain("68%");
    expect(out).toContain("pk-scroll-x");
    expect(out).toContain("[--pk-scroll-cover:var(--color-surface)]");
  });

  it("DataTable sets the scroll cover to the surface it sits on", () => {
    const base = { caption: "c", columns: [{ key: "a", header: "A" }], rows: [{ a: "1" }] };
    expect(html(DataTable<{ a: string }>, { ...base, surface: "inset" })).toContain(
      "[--pk-scroll-cover:var(--color-surface-2)]",
    );
    expect(html(DataTable<{ a: string }>, { ...base, surface: "canvas" })).toContain(
      "[--pk-scroll-cover:var(--color-bg)]",
    );
  });

  it(".pk-scroll-x keeps its own fill: the cover is the last background layer", () => {
    const rule = css.match(/\.pk-scroll-x\s*\{[^}]*\}/)![0];
    expect(rule).toMatch(/,\s*var\(--pk-scroll-cover\);/);
  });
});

describe("design-system hygiene", () => {
  it("has no em dashes in ui sources or globals.css", () => {
    const files = ["Section", "PageHeader", "Card", "Artifact", "Button", "Stat", "StatusPill", "Eyebrow", "DataTable", "SyntheticTag"].map(
      (n) => readFileSync(new URL(`../src/components/ui/${n}.tsx`, import.meta.url), "utf8"),
    );
    for (const f of [...files, css]) expect(f).not.toContain("—");
  });
  it("no longer applies the tilt or the infinite glow animations", () => {
    expect(css).not.toMatch(/\.pk-card-3d:hover/);
    expect(css).not.toMatch(/pkUpsideGlow|pkHeadlineGlow|pkAurora\b/);
    expect(css).not.toMatch(/animation:[^;]*infinite/);
  });
});
