"use client";

import Link from "next/link";

// Slim credibility strip for the landing page. Replaces the prior heavy
// FounderCta section that combined intro + design-partner offer + DM/Email
// CTAs into one card. That hard-sell ask in section 8 of 9 turned off some
// visitors before they had tried the product. The offer + CTAs now live on
// /contact and /pricing where they belong.
//
// What stays on the landing: a single horizontal strip with the founder's
// photo, name, role, three credibility chips, and a quiet "Connect on
// LinkedIn" text link. Enough to answer "who built this?" without selling
// anything.

const NAME = "Adhithya Bhaskar";
const ROLE = "Founder, M.S. Pricing, Simon Business School";
const LINKEDIN =
  process.env.NEXT_PUBLIC_FOUNDER_LINKEDIN ??
  "https://www.linkedin.com/in/adhithyarokhith/";
const AVATAR = "/founder.jpg";

const CHIPS: string[] = [
  "Simon Business School",
  "Pricing + AI",
];

export default function FounderStrip() {
  return (
    <section
      aria-label="Built by"
      className="rounded-2xl border border-mist bg-surface px-6 py-5"
    >
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center sm:gap-5">
        <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-full border border-mist bg-surface-2">
          <span className="absolute inset-0 flex items-center justify-center text-base font-semibold text-teal">
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
          <div className="mt-0.5 text-base font-bold text-fg">{NAME}</div>
          <div className="text-sm text-muted">{ROLE}</div>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-end">
          {CHIPS.map((c) => (
            <span
              key={c}
              className="rounded-md border border-mist bg-surface-2 px-2 py-1 text-[11px] font-semibold text-ink"
            >
              {c}
            </span>
          ))}
        </div>
      </div>
      <div className="mt-3 text-center sm:text-right">
        <Link
          href={LINKEDIN}
          target="_blank"
          rel="noreferrer noopener"
          className="text-xs font-medium text-teal hover:underline"
        >
          Connect on LinkedIn &rarr;
        </Link>
      </div>
    </section>
  );
}
