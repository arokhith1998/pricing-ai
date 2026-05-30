// Direct founder CTA for design partners — answers the reviewer's gap:
// "a direct founder CTA for design partners."
//
// At pre-seed with zero customers, the highest-converting path is not a
// generic "Book a demo" button. It is the founder personally offering to
// run the diagnostic. This block makes that ask explicit.

"use client";

const LINKEDIN =
  process.env.NEXT_PUBLIC_FOUNDER_LINKEDIN ??
  "https://www.linkedin.com/in/adhithyarokhith/";
const EMAIL = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "adhithya@pricekeel.com";

export default function FounderCta() {
  return (
    <section
      aria-label="Founder design-partner CTA"
      className="rounded-2xl border border-teal/40 bg-surface p-6 pk-card-3d"
    >
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center sm:gap-6">
        <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-full border border-teal/40 bg-surface-2">
          <span className="absolute inset-0 flex items-center justify-center text-xl font-semibold text-teal">
            AB
          </span>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/founder.jpg"
            alt="Adhithya Bhaskar, founder"
            className="absolute inset-0 h-full w-full object-cover"
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).style.display = "none";
            }}
          />
        </div>
        <div className="flex-1 text-center sm:text-left">
          <div className="text-xs font-semibold uppercase tracking-wider text-teal">
            Design partner program — open
          </div>
          <div className="mt-0.5 text-lg font-bold text-fg">
            Want me to run the diagnostic on your CSV personally?
          </div>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            I&rsquo;m taking three design partners this quarter. Free
            diagnostic under NDA, 30-minute readout with me, and if the upside
            is real we keep going on a quarterly cadence. If it&rsquo;s not, you
            keep the analysis and we part as friends.
          </p>
          <div className="mt-3 flex flex-wrap items-center justify-center gap-3 sm:justify-start">
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
              Email adhithya@pricekeel.com
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
