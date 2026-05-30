"use client";

import Link from "next/link";

// Founder trust signal. Sourced from Adhithya's pricing portfolio at
// adhi-pricing-ai.vercel.app — kept here so both surfaces stay in sync.
// To swap: replace /web/public/founder.jpg, and edit the constants below.

const NAME = "Adhithya Bhaskar";
const HEADLINE = "Pricing strategist building Pricekeel";
const BIO =
  "M.S. Marketing Analytics with a Pricing specialization from Simon Business School (University of Rochester). Previously led a $626M margin-recovery analysis across 1,200+ opportunities. Building Pricekeel to make that kind of analysis routine for any pricing team, and defensible to finance.";

// Default to the portfolio-known LinkedIn URL; allow env override for later.
const LINKEDIN =
  process.env.NEXT_PUBLIC_FOUNDER_LINKEDIN ?? "https://www.linkedin.com/in/adhithyarokhith/";

const AVATAR = "/founder.jpg"; // 400x400 in /web/public

// Three short credibility lines surfaced as chips — what a CFO buyer asks
// in the first ten seconds of "who built this?"
const CHIPS: { label: string; sub: string }[] = [
  { label: "Simon Business School", sub: "M.S. Marketing Analytics · Pricing" },
  { label: "$626M margin-recovery", sub: "1,200+ opportunities analyzed" },
  { label: "Pricing + AI", sub: "Anthropic Claude certified" },
];

export default function FounderStrip() {
  return (
    <section className="rounded-2xl border border-mist bg-surface p-6">
      <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-start sm:gap-6">
        <div className="relative h-24 w-24 shrink-0 overflow-hidden rounded-full border border-teal/40 bg-surface-2">
          {/* Initials fallback paints first; the image overlays on load. */}
          <span className="absolute inset-0 flex items-center justify-center text-2xl font-semibold text-teal">
            {NAME.split(" ").map((n) => n[0]).join("")}
          </span>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={AVATAR}
            alt={`${NAME}, founder`}
            className="absolute inset-0 h-full w-full object-cover"
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).style.display = "none";
            }}
          />
        </div>
        <div className="flex-1 text-center sm:text-left">
          <div className="text-xs font-semibold uppercase tracking-wider text-teal">
            Built by
          </div>
          <div className="mt-0.5 text-lg font-bold text-fg">{NAME}</div>
          <div className="text-sm font-medium text-fg">{HEADLINE}</div>
          <p className="mt-2 max-w-2xl text-sm text-muted">{BIO}</p>

          {/* Credibility chips */}
          <div className="mt-3 flex flex-wrap justify-center gap-2 sm:justify-start">
            {CHIPS.map((c) => (
              <span
                key={c.label}
                className="inline-flex flex-col items-start rounded-lg border border-mist bg-surface-2 px-2.5 py-1"
              >
                <span className="text-[11px] font-semibold text-fg">
                  {c.label}
                </span>
                <span className="text-[10px] text-muted">{c.sub}</span>
              </span>
            ))}
          </div>

          {LINKEDIN ? (
            <Link
              href={LINKEDIN}
              target="_blank"
              rel="noreferrer noopener"
              className="mt-3 inline-block text-xs font-medium text-teal hover:underline"
            >
              Connect on LinkedIn →
            </Link>
          ) : null}
        </div>
      </div>
    </section>
  );
}
