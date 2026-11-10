import type { Metadata } from "next";
import { Button, Eyebrow, Section } from "@/components/ui";
import HeroHeadline from "@/components/HeroHeadline";
import DiagnosticPreview, { type DiagnosticPreviewData } from "@/components/DiagnosticPreview";
import WhatYouGet from "@/components/WhatYouGet";
import TrustBoundaryStrip from "@/components/TrustBoundaryStrip";
import DecisionRecord from "@/components/landing/DecisionRecord";
import DecisionWalk from "@/components/landing/DecisionWalk";
import { pageMetadata } from "@/lib/page-metadata";
import { OVERVIEW, PROBE_BANDS, RECORD, peakBandLabel } from "@/lib/landing-sample";

// Static marketing landing. No API dependency, so it always loads fast.
export const dynamic = "force-static";

export const metadata: Metadata = pageMetadata({
  title: "Salesforce deal guidance for B2B SaaS",
  description:
    "Pricekeel checks every discount exception in Salesforce against the book before approval and records the decision with its evidence, for B2B SaaS.",
  path: "/",
});

// Every number on this page comes from the bundled synthetic 2,000-deal
// snapshot through src/lib/landing-sample.ts. Nothing is hand-typed.
const PREVIEW_DATA: DiagnosticPreviewData = {
  opportunities: OVERVIEW.opportunities,
  bookedAcvWon: OVERVIEW.booked_acv_won,
  priceRealizationWon: OVERVIEW.price_realization_won,
  avgDiscountWon: OVERVIEW.avg_discount_won,
  winRate: OVERVIEW.win_rate,
  bands: PROBE_BANDS,
  peakBand: peakBandLabel(PROBE_BANDS),
  initialBand: RECORD.requestedBand.label,
};

export default function Landing() {
  return (
    <main id="main" tabIndex={-1} className="outline-none">
      {/* 1. Hero: one claim, one action, the decision record above the fold. */}
      <Section band="canvas" labelledBy="hero-h" className="py-6! md:py-8! lg:py-8!">
        <div className="grid items-center gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,28rem)] lg:gap-12">
          <div>
            <Eyebrow>Salesforce deal guidance for B2B SaaS</Eyebrow>
            <div className="mt-3">
              <HeroHeadline />
            </div>
            <p className="pk-lead m-0 mt-4 max-w-[52ch]">
              Every discount exception is checked against the book before approval. The request
              stays as asked, the evidence is shown, and a person decides.
            </p>
            <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-2">
              <Button href="/contact" size="lg">
                Walk through one discount exception
              </Button>
              <Button href="/sample" variant="quiet">
                See the sample &rarr;
              </Button>
            </div>
            <p className="pk-small m-0 mt-4 text-muted">
              Salesforce orgs with 500+ closed opportunities a year.
            </p>
          </div>
          <DecisionRecord />
        </div>
      </Section>

      {/* 2. Product: the walk through one exception, then the band probe. */}
      <Section band="band" id="workflow" labelledBy="product-h">
        <Eyebrow>How one exception moves</Eyebrow>
        <h2 id="product-h" className="pk-h2 m-0 mt-2">
          One discount exception, from request to outcome.
        </h2>
        <p className="pk-lead m-0 mt-3 max-w-[68ch]">
          The same synthetic deal as above, in four steps. Each step is what the record holds.
        </p>
        <div className="mt-10">
          <DecisionWalk record={RECORD} />
        </div>
        <div className="mt-16">
          <h3 className="pk-h3 m-0">The readout behind it</h3>
          <div className="mt-4">
            <DiagnosticPreview data={PREVIEW_DATA} />
          </div>
        </div>
      </Section>

      {/* 3. Roles: one record, three views. */}
      <Section band="canvas" labelledBy="roles-h">
        <Eyebrow>Who reads it</Eyebrow>
        <h2 id="roles-h" className="pk-h2 m-0 mt-2">
          One decision record, three views.
        </h2>
        <div className="mt-8">
          <WhatYouGet />
        </div>
      </Section>

      {/* 4. Boundary: stated once. */}
      <Section band="band" labelledBy="boundary-h">
        <Eyebrow>Where the engine draws the line</Eyebrow>
        <h2 id="boundary-h" className="pk-h2 m-0 mt-2">
          What it will and will not do.
        </h2>
        <div className="mt-8">
          <TrustBoundaryStrip />
        </div>
      </Section>

      {/* 5. Close. */}
      <Section band="spotlight" labelledBy="close-h" width="prose" className="text-center">
        <Eyebrow>Start a conversation</Eyebrow>
        <h2 id="close-h" className="pk-h2 m-0 mt-2">
          A 20-minute conversation, not a demo.
        </h2>
        <p className="pk-body m-0 mx-auto mt-3 max-w-[56ch]">
          Tell us how discount exceptions get approved today. No data or Salesforce access needed
          to talk.
        </p>
        <div className="mt-6 flex justify-center">
          <Button href="/contact" size="lg">
            Talk to us
          </Button>
        </div>
      </Section>
    </main>
  );
}
