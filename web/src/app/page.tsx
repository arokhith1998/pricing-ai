import Link from "next/link";
import Reveal from "@/components/Reveal";
import HeroHeadline from "@/components/HeroHeadline";
import CountUp from "@/components/CountUp";
import DiagnosticPreview, { type DiagnosticPreviewData } from "@/components/DiagnosticPreview";
import WhatYouGet from "@/components/WhatYouGet";
import TrustBoundaryStrip from "@/components/TrustBoundaryStrip";
import sampleFallback from "@/data/sample-fallback.json";
import type { Diagnostic } from "@/lib/api";

// Static marketing landing. No API dependency, so it always loads fast.
export const dynamic = "force-static";

// The bundled synthetic 2,000-deal snapshot is the single source for every
// number on this page (hero stat and the diagnostic-preview KPIs/chart).
// Nothing here is hand-typed: regenerate the JSON (see src/lib/api.ts) and
// these figures move on their own.
const SAMPLE = sampleFallback as unknown as Diagnostic;

// Segment-aware excess is the headline lens (see pricing-strategist review,
// 2026-09-27): each deal measured against its own segment's reference
// point, not one global threshold. Falls back to the global figure only if
// an older cached payload lacks the segment-aware field.
const HERO_EXCESS =
  SAMPLE.leakage.excess_vs_segment_reference_won ?? SAMPLE.leakage.excess_vs_reference_won;

const DIAGNOSTIC_DATA: DiagnosticPreviewData = {
  opportunities: SAMPLE.overview.opportunities,
  bookedAcvWon: SAMPLE.overview.booked_acv_won,
  priceRealizationWon: SAMPLE.overview.price_realization_won,
  avgDiscountWon: SAMPLE.overview.avg_discount_won,
  excessSegment: HERO_EXCESS,
  excessSegmentPct:
    SAMPLE.leakage.excess_segment_pct_of_booked ?? SAMPLE.leakage.excess_pct_of_booked,
  winRate: SAMPLE.overview.win_rate,
  bands: SAMPLE.win_rate_by_band.map((b) => ({
    label: b.discount_band,
    winRate: b.win_rate,
    isReference: b.discount_band === SAMPLE.reference_discount.reference_band,
  })),
};

export default function Landing() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      {/* 1. Hero: one sentence, one real number, one action. */}
      <Reveal>
        <section className="flex min-h-[100svh] flex-col items-center justify-center py-10 text-center">
          <p className="mb-4 text-xs font-semibold uppercase tracking-[0.2em] text-teal">
            Salesforce deal guidance for B2B SaaS
          </p>
          <HeroHeadline />
          <div className="mt-10">
            <div className="text-5xl font-extrabold tabular-nums text-coral sm:text-6xl">
              <CountUp to={HERO_EXCESS} format="moneyShort" />
            </div>
            <p className="mx-auto mt-2 max-w-md text-sm text-muted">
              sits below the segment&rsquo;s win point on the sample book
            </p>
          </div>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/contact"
              className="rounded-lg bg-teal px-5 py-3 font-semibold text-bg transition hover:-translate-y-0.5 hover:bg-teal/90"
            >
              Walk through one discount exception
            </Link>
            <Link
              href="/sample"
              className="text-sm font-medium text-muted underline-offset-4 transition hover:text-teal hover:underline"
            >
              See the live sample &rarr;
            </Link>
          </div>
          <p className="mt-8 text-xs text-muted">
            Salesforce orgs with 500+ closed opportunities a year.
          </p>
        </section>
      </Reveal>

      {/* 2. The one immersive product mockup, revealed on scroll. */}
      <Reveal inView>
        <section id="workflow" className="mt-8 scroll-mt-24">
          <DiagnosticPreview data={DIAGNOSTIC_DATA} />
        </section>
      </Reveal>

      {/* 3. What you get, one line per role. */}
      <Reveal inView>
        <section className="mt-20">
          <WhatYouGet />
        </section>
      </Reveal>

      {/* 4. Trust and boundary, stated once. */}
      <Reveal inView>
        <section className="mt-16">
          <TrustBoundaryStrip />
        </section>
      </Reveal>

      {/* 5. Closing CTA. */}
      <Reveal inView>
        <section className="mt-16 rounded-2xl border border-teal/40 bg-surface px-6 py-10 text-center sm:px-10">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal">
            Design-partner cohort
          </p>
          <h2 className="mt-2 text-2xl font-bold text-fg">A 20-minute conversation, not a demo.</h2>
          <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-muted">
            Tell us how discount exceptions get approved today. No data or
            Salesforce access needed to talk.
          </p>
          <div className="mt-6 flex justify-center">
            <Link href="/contact" className="rounded-lg bg-teal px-5 py-3 font-semibold text-bg hover:bg-teal/90">
              Talk to us
            </Link>
          </div>
        </section>
      </Reveal>
    </main>
  );
}
