// Single founder section. Replaced the prior split between FounderStrip
// (intro with bio + chips) and FounderCta (the design-partner offer) which
// were rendering the same photo back-to-back on the landing. One face, one
// section, one action.
//
// At pre-seed with zero customers, the highest-converting path is not a
// generic "Book a demo" button. It is the founder personally offering to
// run the diagnostic, with enough credentials in the same card that the
// reader does not have to leave the page to vet who is making the offer.

"use client";

import Link from "next/link";

const NAME = "Adhithya Bhaskar";
const LINKEDIN =
  process.env.NEXT_PUBLIC_FOUNDER_LINKEDIN ??
  "https://www.linkedin.com/in/adhithyarokhith/";
const EMAIL = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "adhithya@pricekeel.com";

// Three short credibility lines, kept inline so the reader can vet the
// founder without clicking through to LinkedIn.
const CHIPS: { label: string; sub: string }[] = [
  { label: "Simon Business School", sub: "M.S. Marketing Analytics, Pricing" },
  { label: "$626M margin-recovery", sub: "1,200+ opportunities analyzed" },
  { label: "Pricing + AI", sub: "Anthropic Claude certified" },
];

export default function FounderCta() {
  return (
    <section
      aria-label="Founder design-partner offer"
      className="rounded-2xl border border-teal/40 bg-surface p-6 pk-card-3d"
    >
      <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-start sm:gap-6">
        <div className="relative h-24 w-24 shrink-0 overflow-hidden rounded-full border border-teal/40 bg-surface-2">
          <span className="absolute inset-0 flex items-center justify-center text-2xl font-semibold text-teal">
            {NAME.split(" ").map((n) => n[0]).join("")}
          </span>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/founder.jpg"
            alt={`${NAME}, founder`}
            className="absolute inset-0 h-full w-full object-cover"
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).style.display = "none";
            }}
          />
        </div>
        <div className="flex-1 text-center sm:text-left">
          <div className="text-xs font-semibold uppercase tracking-wider text-teal">
            Design partner program, open
          </div>
          <div className="mt-0.5 text-lg font-bold text-fg">
            Want me to run the diagnostic on your CSV personally?
          </div>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            I&rsquo;m taking three design partners this quarter. Free
            diagnostic under NDA, 30-minute readout with me, and if the
            upside is real we keep going on a quarterly cadence. If
            it&rsquo;s not, you keep the analysis and we part as friends.
          </p>

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

          <div className="mt-4 flex flex-wrap items-center justify-center gap-3 sm:justify-start">
            <a
              href={LINKEDIN}
              target="_blank"
              rel="noreferrer noopener"
              className="rounded-lg bg-teal px-4 py-2 text-sm font-semibold text-bg transition hover:scale-[1.02]"
            >
              DM me on LinkedIn
            </a>
            <a
              href={`mailto:${EMAIL}?subject=Pricekeel%20design%20partner`}
              className="rounded-lg border border-mist bg-surface-2 px-4 py-2 text-sm font-medium text-fg transition hover:border-teal"
            >
              Email {EMAIL}
            </a>
            <Link
              href={LINKEDIN}
              target="_blank"
              rel="noreferrer noopener"
              className="text-xs font-medium text-slate underline-offset-4 hover:text-teal hover:underline"
            >
              See full LinkedIn profile
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
