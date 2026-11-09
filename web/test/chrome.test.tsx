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
  APP_ROUTES,
  FOOTER_COLUMNS,
  GLOBAL_DISCLOSURE,
  PRIMARY_NAV,
  isCurrent,
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
  it("lists Product, Sample, Calculator, Pricing, Trust, a login and the primary CTA, and drops Blog and Live sample", () => {
    const c = nav("/");
    const desktop = c.querySelector('nav[aria-label="Primary"]')!;
    expect([...desktop.querySelectorAll("a")].map((a) => a.textContent)).toEqual([
      "Product",
      "Sample",
      "Calculator",
      "Pricing",
      "Trust",
    ]);
    const text = c.textContent ?? "";
    expect(text).toContain("Customer login");
    expect(text).toContain("Talk to us");
    expect(text).not.toContain("Live sample");
    expect(text).not.toContain("Blog");
    const cta = [...c.querySelectorAll("a")].find((a) => a.textContent === "Talk to us")!;
    expect(cta.getAttribute("href")).toBe("/contact");
    expect(cta.className).toContain("bg-teal");
    expect(cta.className).toContain("text-bg");
    const login = [...c.querySelectorAll("a")].find((a) => a.textContent === "Customer login")!;
    expect(login.getAttribute("href")).toBe("/login");
    expect(login.className).not.toContain("bg-teal");
  });

  it("mobile menu is a native details element with 48px rows, no JS needed", () => {
    const c = nav("/");
    const details = c.querySelector("details")!;
    expect(details).not.toBeNull();
    expect(details.querySelector("summary")).not.toBeNull();
    const mobileLinks = [...details.querySelectorAll("nav a")];
    expect(mobileLinks.length).toBe(PRIMARY_NAV.length + 2);
    for (const a of mobileLinks) expect(a.className).toContain("min-h-12");
    // Server-rendered markup (no hydration) already contains the menu and links.
    mockPath = "/";
    const html = renderToStaticMarkup(<Nav />);
    expect(html).toContain("<details");
    expect(html).toContain("Talk to us");
  });

  it.each([
    ["/", ["/"]],
    ["/sample", ["/sample"]],
    ["/calculator", ["/calculator"]],
    ["/pricing", ["/pricing"]],
    ["/trust", ["/trust"]],
    ["/login", ["/login"]],
    ["/contact", ["/contact"]],
    ["/blog", []],
    ["/blog/some-post", []],
    ["/methodology", []],
    ["/crm", []],
  ])("aria-current on %s", (path, expected) => {
    const c = nav(path);
    // Each link renders in both the desktop bar and the mobile sheet.
    const found = new Set(currents(c));
    expect([...found].sort()).toEqual([...expected].sort());
  });

  it("never marks the Product hash link as the current page", () => {
    expect(isCurrent("/", "/#workflow")).toBe(false);
  });

  it("a nested path keeps its parent current", () => {
    expect(isCurrent("/sample/full", "/sample")).toBe(true);
    expect(isCurrent("/samples", "/sample")).toBe(false);
  });
});

describe("Footer", () => {
  it("renders four labelled columns built from site-nav", () => {
    mockPath = "/";
    const { container } = render(<Footer />);
    const titles = [...container.querySelectorAll("h2")].map((h) => h.textContent);
    expect(titles).toEqual(["Product", "Company", "Trust and legal", "Customers"]);
    expect(FOOTER_COLUMNS.map((c) => c.title)).toEqual(titles);
  });

  it("keeps every link the old footer had, including Blog", () => {
    mockPath = "/";
    const { container } = render(<Footer />);
    const hrefs = new Set([...container.querySelectorAll("a")].map((a) => a.getAttribute("href")));
    for (const h of [
      "/sample", "/crm", "/calculator", "/pricing", "/contact", "/blog", "/brand",
      "/trust", "/privacy", "/terms", "/subprocessors", "/licenses", "/upload",
    ]) {
      expect(hrefs.has(h), h).toBe(true);
    }
  });

  it("footer links are at least 44px tall (min-h-11)", () => {
    mockPath = "/";
    const { container } = render(<Footer />);
    for (const a of container.querySelectorAll("a")) expect(a.className).toContain("min-h-11");
  });

  it("shows the one global disclosure on public routes", () => {
    mockPath = "/pricing";
    const { container } = render(<Footer />);
    expect(container.textContent).toContain(
      "Every figure on this site comes from a synthetic 2,000-deal sample, not customer data.",
    );
    expect(GLOBAL_DISCLOSURE).toBe(
      "Every figure on this site comes from a synthetic 2,000-deal sample, not customer data.",
    );
    expect((container.textContent!.match(/synthetic 2,000-deal sample/g) ?? []).length).toBe(1);
  });

  it.each(APP_ROUTES)("hides the disclosure on app route %s", (route) => {
    mockPath = route;
    const { container } = render(<Footer />);
    expect(container.textContent).not.toContain("not customer data");
  });
});

describe("ChromeEffects", () => {
  it("renders the scroll bar only on /blog/*, /methodology and /trust", () => {
    const withBar = ["/blog/a-post", "/methodology", "/trust"];
    const without = ["/", "/pricing", "/calculator", "/sample", "/login", "/blog", "/contact"];
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
    mockPath = "/pricing";
    render(<ChromeEffects />);
    expect(document.querySelector("main")!.id).toBe("main");
    document.body.innerHTML = "";
  });
});

describe("layout", () => {
  const src = readFileSync(resolve(process.cwd(), "src/app/layout.tsx"), "utf8");
  it("keeps the title template, default title and the analytics gate", () => {
    expect(src).toContain('template: "%s · Pricekeel"');
    expect(src).toContain('const DEFAULT_TITLE = "Pricekeel · Salesforce deal guidance for B2B SaaS"');
    expect(src).toContain('process.env.NEXT_PUBLIC_VERCEL_ANALYTICS_ENABLED === "true"');
  });
  it("renders a skip link to #main and documents the main contract", () => {
    expect(src).toContain('href="#main"');
    expect(src).toContain("Skip to content");
    expect(src).toContain('<main id="main" tabIndex={-1}>');
  });
});
