// @vitest-environment jsdom
//
// PK-116 (F17): the site is cut to one offer. This file pins the /contact page,
// the /pricing redirect, the noindex routes, the sitemap, the trust, privacy
// and terms statements, the single call to action, and the repo-wide bans
// (em dash, ADR-006 margin wording, proof words) over every changed page.
import { readFileSync } from "node:fs";
import { createElement } from "react";
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import nextConfig from "../next.config";
import ContactPage, { metadata as contactMeta } from "@/app/contact/page";
import TrustPage from "@/app/trust/page";
import PrivacyPage from "@/app/privacy/page";
import TermsPage from "@/app/terms/page";
import Landing from "@/app/page";
import AuditPage from "@/app/audit/page";
import { metadata as calculatorMeta } from "@/app/calculator/page";
import { metadata as methodologyMeta } from "@/app/methodology/page";
import sitemap from "@/app/sitemap";
import { BOOKING_LABEL, BOOKING_URL } from "@/lib/site-nav";
import { marginViolations, stringLiterals } from "./cost-basis-guard";

afterEach(cleanup);

const pages: Record<string, () => ReturnType<typeof render>> = {
  "/": () => render(createElement(Landing)),
  "/audit": () => render(createElement(AuditPage)),
  "/contact": () => render(createElement(ContactPage)),
  "/trust": () => render(createElement(TrustPage)),
  "/privacy": () => render(createElement(PrivacyPage)),
  "/terms": () => render(createElement(TermsPage)),
};

function words(container: HTMLElement): number {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  const parts: string[] = [];
  while (walker.nextNode()) parts.push(walker.currentNode.textContent ?? "");
  return parts.join(" ").split(/\s+/).filter(Boolean).length;
}

const read = (f: string) => readFileSync(f, "utf8");

describe("/contact", () => {
  it("is under 120 words, one h1, conversation first", () => {
    const { container } = pages["/contact"]();
    expect(words(container)).toBeLessThan(120);
    expect(container.querySelectorAll("h1")).toHaveLength(1);
    expect(container.querySelector("h1")?.textContent).toBe("Twenty minutes on how you price per unit");
    const t = container.textContent ?? "";
    expect(t).toContain(
      "I am talking to fifteen AI founders about how they decide what to charge per unit, and how they find which customers cost more to serve than they pay. It is a conversation, not a pitch. No data, no access, no preparation.",
    );
    expect(t).toContain("Prefer a one-line answer? Email adhithya@pricekeel.com. I share what I learn, anonymised.");
    for (const gone of ["design-partner", "Salesforce", "access code", "discount exception", "Subject:", "LinkedIn"]) {
      expect(t, gone).not.toContain(gone);
    }
  });

  it("has the booking button and the email link only", () => {
    const { container } = pages["/contact"]();
    const links = [...container.querySelectorAll("main a")];
    expect(links.map((a) => [a.textContent, a.getAttribute("href")])).toEqual([
      [BOOKING_LABEL, BOOKING_URL],
      ["adhithya@pricekeel.com", "mailto:adhithya@pricekeel.com"],
    ]);
  });

  it("uses a bare title so the layout renders Contact · Pricekeel once", () => {
    expect(contactMeta.title).toBe("Contact");
    expect(JSON.stringify(contactMeta)).not.toContain("Pricekeel ·");
    expect(read("src/app/layout.tsx")).toContain('template: "%s · Pricekeel"');
  });
});

describe("single call to action", () => {
  it("is one label and one constant, defaulting to a mailto", () => {
    expect(BOOKING_LABEL).toBe("Book a 20-minute call");
    expect(BOOKING_URL).toBe("mailto:adhithya@pricekeel.com?subject=20%20minutes%20on%20pricing");
    for (const route of ["/", "/audit", "/contact"]) {
      const { container } = pages[route]();
      const buttons = [...container.querySelectorAll("main a")].filter((a) => a.className.includes("bg-teal"));
      expect(buttons, route).toHaveLength(1);
      expect(buttons[0].textContent).toBe(BOOKING_LABEL);
      expect(buttons[0].getAttribute("href")).toBe(BOOKING_URL);
      cleanup();
    }
    for (const f of ["src/app/page.tsx", "src/app/audit/page.tsx", "src/app/contact/page.tsx", "src/components/Nav.tsx"]) {
      expect(read(f), f).not.toContain("Book a 20-minute call");
      expect(read(f), f).not.toContain("mailto:adhithya@pricekeel.com?subject");
    }
    expect(read("src/lib/site-nav.ts")).not.toMatch(/Talk to us|Request the audit/);
  });
});

describe("/pricing", () => {
  it("is a permanent redirect to /audit and the page is gone", async () => {
    const redirects = await nextConfig.redirects!();
    expect(redirects).toContainEqual({ source: "/pricing", destination: "/audit", permanent: true });
    expect(() => read("src/app/pricing/page.tsx")).toThrow();
  });
});

describe("unlinked routes", () => {
  it("calculator and methodology are noindex", () => {
    expect(calculatorMeta.robots).toMatchObject({ index: false });
    expect(methodologyMeta.robots).toMatchObject({ index: false });
  });

  it.each([
    "src/app/sample/page.tsx",
    "src/app/blog/page.tsx",
    "src/app/blog/[slug]/page.tsx",
    "src/app/crm/page.tsx",
    "src/app/upload/page.tsx",
  ])("%s sets robots index false", (f) => {
    expect(read(f)).toMatch(/robots: \{ index: false \}/);
  });

  it("no unlinked page carries a Connect Salesforce or unlock call to action", () => {
    for (const f of ["src/app/calculator/page.tsx", "src/components/LeakageCalculator.tsx", "src/app/sample/page.tsx", "src/components/LeadForm.tsx"]) {
      const src = read(f);
      expect(src, f).not.toContain("Connect Salesforce");
      expect(src, f).not.toMatch(/Unlock the full|Unlocking/);
    }
  });
});

describe("sitemap", () => {
  it("lists only the linked pages", () => {
    const urls = sitemap().map((e) => e.url.replace("https://www.pricekeel.com", ""));
    expect(urls).toEqual(["/", "/audit", "/contact", "/trust", "/privacy", "/terms"]);
    for (const gone of ["/pricing", "/sample", "/calculator", "/blog", "/methodology", "/crm", "/upload", "/subprocessors", "/licenses"]) {
      expect(urls.some((u) => u.startsWith(gone)), gone).toBe(false);
    }
  });
});

describe("/trust", () => {
  it("states the five honest lines and nothing the product cannot back", () => {
    const { container } = pages["/trust"]();
    const t = container.textContent ?? "";
    for (const line of [
      "Pricekeel is run by one founder. We accept no customer files until a mutual NDA and data addendum are signed.",
      "We work only from exports you send: no API keys, no system connections, no end-user personal data.",
      "Files are used only to deliver your audit. They are not used to improve models that benefit other customers without your written consent.",
      "We delete them within 30 days of the engagement ending and confirm it in writing.",
      "We are not SOC 2 certified.",
      "Ask adhithya@pricekeel.com anything specific.",
    ]) {
      expect(t).toContain(line);
    }
    expect(container.querySelectorAll("h1")).toHaveLength(1);
    for (const gone of [
      "Standard Contractual Clauses", "controls live", "Access codes are issued", "copilot", "ompetitor",
      "system prompt", "OAuth", "Salesforce", "Anthropic", "Pre-SOC",
    ]) {
      expect(t, gone).not.toContain(gone);
    }
  });
});

describe("/privacy and /terms", () => {
  it("privacy is consistent with 30-day deletion and keeps the lead form and cookie content", () => {
    const t = pages["/privacy"]().container.textContent ?? "";
    expect(t).toContain("Last updated 11 November 2026");
    expect(t).toContain("within 30 days of the engagement ending");
    expect(t).not.toMatch(/No automatic purge|Standard Contractual|Salesforce|copilot|Competitor|Anthropic|system prompt/);
    expect(t).toContain("When you request the full sample, we collect your name");
    expect(t).toContain("pk_lead");
    expect(t).toContain("Vercel Web Analytics");
    expect(t).toContain("Server logs:");
  });

  it("terms invent no entity or governing law and defer to the engagement letter", () => {
    const t = pages["/terms"]().container.textContent ?? "";
    expect(t).toContain("Last updated 11 November 2026");
    expect(t).toContain("will be provided with the engagement letter");
    expect(t).not.toMatch(/Delaware|New Castle|\[legal entity\]|Inc\.|LLC|Salesforce|copilot|competitor/i);
    expect(read("src/app/terms/page.tsx")).not.toContain("@/lib/legal");
  });
});

describe("banned wording on every linked page", () => {
  it.each(Object.keys(pages))("%s has no em dash, proof, tier, Salesforce or ADR-006 violation", (route) => {
    const { container } = pages[route]();
    const t = container.textContent ?? "";
    expect(t).not.toContain("—");
    expect(t.toLowerCase()).not.toMatch(
      /low five figures|free for design partners|operate tier|operate plan|diagnostic tier|salesforce|proven|testimonial|case stud|our customers/,
    );
    expect(container.querySelectorAll("h1"), route).toHaveLength(1);
    expect(marginViolations(t)).toEqual([]);
  });

  it("every changed source file is free of em dashes and ADR-006 violations", () => {
    for (const f of [
      "src/app/page.tsx", "src/app/audit/page.tsx", "src/app/contact/page.tsx", "src/app/trust/page.tsx",
      "src/app/privacy/page.tsx", "src/app/terms/page.tsx", "src/app/sitemap.ts", "src/lib/site-nav.ts",
      "src/components/Nav.tsx", "src/components/Footer.tsx", "src/lib/audit-offer.ts",
    ]) {
      const src = read(f);
      expect(src, f).not.toContain("—");
      for (const lit of stringLiterals(src)) expect(marginViolations(lit), `${f}: ${lit}`).toEqual([]);
    }
  });

  it("nav and footer sources never mention the removed tiers or Salesforce", () => {
    const nav = read("src/lib/site-nav.ts");
    expect(nav).not.toMatch(/Salesforce|low five figures|design partner|Operate|Diagnostic tier/i);
  });
});
