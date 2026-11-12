// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

let mockPath = "/";
vi.mock("next/navigation", () => ({ usePathname: () => mockPath }));

import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import ChromeEffects from "@/components/ChromeEffects";
import {
  BOOKING_LABEL,
  BOOKING_URL,
  DISCLOSURE_ROUTES,
  FOOTER_COLUMNS,
  GLOBAL_DISCLOSURE,
  PRIMARY_NAV,
  isCurrent,
  showsDisclosure,
  showsScrollProgress,
} from "@/lib/site-nav";

afterEach(() => cleanup());

function nav(path: string) {
  mockPath = path;
  const { container } = render(<Nav />);
  return container;
}
function currents(container: HTMLElement) {
  return [...container.querySelectorAll('[aria-current="page"]')].map(
    (el) => el.getAttribute("href"),
  );
}

describe("Nav", () => {
  it("is the logo, Audit, Contact and the booking button, and nothing else", () => {
    const c = nav("/");
    const desktop = c.querySelector('nav[aria-label="Primary"]')!;
    expect([...desktop.querySelectorAll("a")].map((a) => [a.textContent, a.getAttribute("href")])).toEqual([
      ["Audit", "/audit"],
      ["Contact", "/contact"],
    ]);
    expect(PRIMARY_NAV).toHaveLength(2);
    const logo = c.querySelector('a[aria-label="Pricekeel home"]')!;
    expect(logo.getAttribute("href")).toBe("/");
    // Every link in the header, desktop and mobile: logo, 2 links, button, each of those twice minus the logo.
    const all = [...c.querySelectorAll("a")].map((a) => a.textContent);
    expect(all.filter((t) => t === "Audit")).toHaveLength(2);
    expect(all.filter((t) => t === "Contact")).toHaveLength(2);
    expect(all.filter((t) => t === BOOKING_LABEL)).toHaveLength(2);
    expect(all).toHaveLength(7);
    const text = c.textContent ?? "";
    for (const gone of ["Customer login", "Talk to us", "Sample", "Calculator", "Product", "Blog", "Trust"]) {
      expect(text, gone).not.toContain(gone);
    }
  });

  it("the primary button is the one booking label and constant", () => {
    const c = nav("/");
    const cta = [...c.querySelectorAll("a")].find((a) => a.textContent === "Book a 20-minute call")!;
    expect(BOOKING_LABEL).toBe("Book a 20-minute call");
    expect(BOOKING_URL).toBe("mailto:adhithya@pricekeel.com?subject=20%20minutes%20on%20pricing");
    expect(cta.getAttribute("href")).toBe(BOOKING_URL);
    expect(cta.className).toContain("bg-teal");
    expect(cta.className).toContain("text-bg");
  });

  it("mobile menu is a native details element with 48px rows, no JS needed", () => {
    const c = nav("/");
    const details = c.querySelector("details")!;
    expect(details).not.toBeNull();
    expect(details.querySelector("summary")).not.toBeNull();
    const mobileLinks = [...details.querySelectorAll("nav a")];
    expect(mobileLinks.length).toBe(PRIMARY_NAV.length + 1);
    for (const a of mobileLinks) expect(a.className).toContain("min-h-12");
    mockPath = "/";
    const html = renderToStaticMarkup(<Nav />);
    expect(html).toContain("<details");
    expect(html).toContain("Book a 20-minute call");
  });

  it.each([
    ["/", ["/"]],
    ["/audit", ["/audit"]],
    ["/contact", ["/contact"]],
    ["/trust", []],
    ["/sample", []],
    ["/blog/some-post", []],
  ])("aria-current on %s", (path, expected) => {
    const c = nav(path);
    const found = new Set(currents(c));
    expect([...found].sort()).toEqual([...expected].sort());
  });

  it("never marks a hash link as the current page", () => {
    expect(isCurrent("/", "/#workflow")).toBe(false);
  });

  it("a nested path keeps its parent current", () => {
    expect(isCurrent("/audit/x", "/audit")).toBe(true);
    expect(isCurrent("/auditx", "/audit")).toBe(false);
  });
});

describe("Footer", () => {
  it("renders without React key or other console errors", () => {
    const err = vi.spyOn(console, "error").mockImplementation(() => {});
    mockPath = "/";
    render(<Footer />);
    expect(err).not.toHaveBeenCalled();
    err.mockRestore();
  });

  it("has exactly three links: Trust, Privacy, Terms", () => {
    mockPath = "/";
    const { container } = render(<Footer />);
    expect([...container.querySelectorAll("a")].map((a) => [a.textContent, a.getAttribute("href")])).toEqual([
      ["Trust", "/trust"],
      ["Privacy", "/privacy"],
      ["Terms", "/terms"],
    ]);
    expect(FOOTER_COLUMNS.flatMap((c) => c.links)).toHaveLength(3);
    const hrefs = new Set([...container.querySelectorAll("a")].map((a) => a.getAttribute("href")));
    for (const h of [
      "/sample", "/crm", "/calculator", "/pricing", "/contact", "/blog", "/brand",
      "/subprocessors", "/licenses", "/upload", "/methodology",
    ]) {
      expect(hrefs.has(h), h).toBe(false);
    }
  });

  it("footer links are at least 44px tall (min-h-11)", () => {
    mockPath = "/";
    const { container } = render(<Footer />);
    for (const a of container.querySelectorAll("a")) expect(a.className).toContain("min-h-11");
  });

  it("shows no synthetic-figures disclosure on any linked page", () => {
    for (const route of ["/", "/audit", "/contact", "/trust", "/privacy", "/terms"]) {
      mockPath = route;
      const { container } = render(<Footer />);
      expect(container.textContent, route).not.toContain("synthetic");
      expect(showsDisclosure(route)).toBe(false);
      cleanup();
    }
  });

  it("shows the one global disclosure only on the unlinked routes that carry figures", () => {
    const LINE =
      "Figures on this site come from a synthetic 2,000-deal sample or are illustrative. None is customer data.";
    expect(GLOBAL_DISCLOSURE).toBe(LINE);
    expect([...DISCLOSURE_ROUTES].sort()).toEqual(
      ["/blog", "/calculator", "/diagnostic", "/guidance", "/methodology", "/sample"],
    );
    for (const route of DISCLOSURE_ROUTES) {
      mockPath = route;
      const { container } = render(<Footer />);
      expect((container.textContent!.match(/synthetic 2,000-deal sample/g) ?? []).length, route).toBe(1);
      cleanup();
    }
  });
});

describe("ChromeEffects", () => {
  it("renders the scroll bar only on /blog/*, /methodology and /trust", () => {
    const withBar = ["/blog/a-post", "/methodology", "/trust"];
    const without = ["/", "/audit", "/calculator", "/sample", "/login", "/blog", "/contact"];
    for (const p of withBar) {
      mockPath = p;
      const { container } = render(<ChromeEffects />);
      expect(container.querySelector(".pk-scroll-progress"), p).not.toBeNull();
      cleanup();
    }
    for (const p of without) {
      mockPath = p;
      const { container } = render(<ChromeEffects />);
      expect(container.querySelector(".pk-scroll-progress"), p).toBeNull();
      cleanup();
      expect(showsScrollProgress(p)).toBe(false);
    }
  });

  it("renders one static spotlight, and nothing on the legal routes", () => {
    mockPath = "/";
    const { container } = render(<ChromeEffects />);
    expect(container.querySelectorAll(".pk-spotlight")).toHaveLength(1);
    cleanup();
    for (const p of ["/privacy", "/terms", "/licenses", "/subprocessors"]) {
      mockPath = p;
      const r = render(<ChromeEffects />);
      expect(r.container.innerHTML, p).toBe("");
      cleanup();
    }
  });

  it("chrome sources have no framer-motion, parallax or infinite animation", () => {
    for (const f of ["AuroraBackground", "ScrollProgress", "ChromeEffects"]) {
      const src = readFileSync(resolve(process.cwd(), `src/components/${f}.tsx`), "utf8");
      const code = src.split("\n").filter((l) => !l.trim().startsWith("//")).join("\n");
      expect(code, f).not.toMatch(/framer-motion|useScroll|useTransform/);
    }
  });

  it("gives an unmigrated page's <main> the skip-link target id", () => {
    document.body.innerHTML = "<main>page</main>";
    mockPath = "/audit";
    render(<ChromeEffects />);
    expect(document.querySelector("main")!.id).toBe("main");
    document.body.innerHTML = "";
  });
});

describe("layout", () => {
  const src = readFileSync(resolve(process.cwd(), "src/app/layout.tsx"), "utf8");
  it("keeps the title template, default title and the analytics gate", () => {
    expect(src).toContain('template: "%s · Pricekeel"');
    expect(src).toContain('const DEFAULT_TITLE = "Pricekeel · Pricing for AI and B2B software companies"');
    expect(src).toContain('process.env.NEXT_PUBLIC_VERCEL_ANALYTICS_ENABLED === "true"');
  });
  it("renders a skip link to #main and documents the main contract", () => {
    expect(src).toContain('href="#main"');
    expect(src).toContain("Skip to content");
    expect(src).toContain('<main id="main" tabIndex={-1}>');
  });
});
