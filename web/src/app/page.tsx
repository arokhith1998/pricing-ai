import type { Metadata } from "next";
import { Button, Card, Eyebrow, Section, StatusIcons, StatusPill } from "@/components/ui";
import { moneyShort, pct } from "@/lib/format";
import HeroHeadline from "@/components/HeroHeadline";
import DiagnosticPreview, { type DiagnosticPreviewData } from "@/components/DiagnosticPreview";
import WhatYouGet from "@/components/WhatYouGet";
import TrustBoundaryStrip from "@/components/TrustBoundaryStrip";
import DecisionRecord from "@/components/landing/DecisionRecord";
import DecisionWalk from "@/components/landing/DecisionWalk";
import Bottlenecks from "@/components/landing/Bottlenecks";
import { pageMetadata } from "@/lib/page-metadata";
import { AUDIT_DAYS, AUDIT_PRICE } from "@/lib/audit-offer";
import { HERO_EXCESS, HERO_EXCESS_PCT, OVERVIEW, PROBE_BANDS, RECORD, peakBandLabel } from "@/lib/landing-sample";

// Static marketing landing. No API dependency, so it always loads fast.
export const dynamic = "force-static";

export const metadata: Metadata = pageMetadata({
  title: "A 14-day pricing audit for AI companies",
  description:
    "We stop AI companies from losing money on heavy users. A done-for-you 14-day pricing audit for B2B and AI SaaS moving to usage or outcome pricing.",
  path: "/",
});

// Every number on this page comes from the bundled synthetic 2,000-deal
// snapshot through src/lib/landing-sample.ts, or from the audit terms in
// src/lib/audit-offer.ts. Nothing else is hand-typed.
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
      {/* 1. Hero: the AI pricing bottleneck, one line of positioning, one action. */}
      <Section band="canvas" labelledBy="hero-h" className="py-6! md:py-8! lg:py-8!">
        <div className="grid items-center gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)] lg:gap-12">
          <div data-testid="hero">
            <Eyebrow>The AI pricing bottleneck</Eyebrow>
            <div className="mt-3">
              <HeroHeadline />
            </div>
            <p className="pk-lead m-0 mt-4 max-w-[56ch]">
              Inference and storage costs are real and variable, per-seat revenue shrinks as your
              product gets better, and buyers want a bill they can budget. Pricekeel is for B2B and
              AI SaaS companies moving from flat or per-seat to usage or outcome pricing.
            </p>
            <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-3">
              <Button href="/audit" size="lg">
                See the 14-day audit
              </Button>
              <p className="pk-small m-0 text-muted" data-testid="calculator-coming">
                <span className="font-semibold text-fg">AI pricing audit calculator:</span> coming
              </p>
            </div>
          </div>
          <aside data-testid="audit-glance">
            <Card className="p-5 sm:p-6">
              <p className="pk-eyebrow m-0">The audit at a glance</p>
              <dl className="m-0 mt-3 grid gap-3">
                <div>
                  <dt className="pk-small text-muted">Delivered</dt>
                  <dd className="m-0 font-semibold text-fg">By a person, done for you</dd>
                </div>
                <div>
                  <dt className="pk-small text-muted">Time</dt>
                  <dd className="m-0 font-semibold text-fg">{AUDIT_DAYS} days from validated intake</dd>
                </div>
                <div>
                  <dt className="pk-small text-muted">Fee</dt>
                  <dd className="m-0 font-semibold text-fg">{AUDIT_PRICE} fixed, paid upfront</dd>
                </div>
                <div>
                  <dt className="pk-small text-muted">What we take</dt>
                  <dd className="m-0 font-semibold text-fg">Exports only, no API keys</dd>
                </div>
              </dl>
              <p className="pk-small m-0 mt-4 border-t border-border pt-3 text-muted">
                You decide every pricing change. We recommend, with the evidence.
              </p>
            </Card>
          </aside>
        </div>
      </Section>

      {/* 2. The six bottlenecks, as the research sheet lists them. */}
      <Section band="band" id="bottlenecks" labelledBy="bottlenecks-h">
        <Eyebrow>Where AI pricing breaks</Eyebrow>
        <h2 id="bottlenecks-h" className="pk-h2 m-0 mt-2">
          Six bottlenecks that do not exist in traditional software.
        </h2>
        <p className="pk-lead m-0 mt-3 max-w-[68ch]">
          This is our reading of what AI founders, operators and investors describe. They are the
          questions the audit asks of your own numbers, not findings about your company.
        </p>
        <div className="mt-8">
          <Bottlenecks />
        </div>
      </Section>

      {/* 3. The offer, short. The full page is /audit. */}
      <Section band="canvas" labelledBy="audit-h">
        <Eyebrow>Start here</Eyebrow>
        <h2 id="audit-h" className="pk-h2 m-0 mt-2">
          A {AUDIT_DAYS}-day pricing audit, done for you.
        </h2>
        <p className="pk-lead m-0 mt-3 max-w-[68ch]">
          From your billing and cost exports, we show which customers and plans your inference and
          storage costs leave with thin or negative contribution margin, customer-supplied cost
          basis. Then we recommend a packaging structure for you to decide on.
        </p>
        <ul className="pk-body m-0 mt-5 max-w-[68ch] list-disc space-y-2 pl-5 text-muted marker:text-teal">
          <li>{AUDIT_PRICE} fixed, paid upfront. No share of results.</li>
          <li>The clock starts when your exports pass our readiness check.</li>
          <li>
            No guarantee of recovered revenue. The audit is analytical and advisory, and every
            pricing decision stays with you.
          </li>
        </ul>
        <div className="mt-6">
          <Button href="/audit" size="lg">
            See what the audit covers
          </Button>
        </div>
      </Section>

      {/* 4. What the product does today: the live Salesforce deal-guidance diagnostic. */}
      <Section band="band" id="workflow" labelledBy="product-h">
        <Eyebrow>What the product does today</Eyebrow>
        <h2 id="product-h" className="pk-h2 m-0 mt-2">
          Live now: Salesforce deal guidance for discount exceptions.
        </h2>
        <p className="pk-lead m-0 mt-3 max-w-[68ch]">
          The built product checks every discount exception in Salesforce against the book before
          approval. The request stays as asked, the evidence is shown, and a person decides. It is
          for Salesforce orgs with 500+ closed opportunities a year. The pricing audit above is a
          separate, done-for-you service.
        </p>
        <div className="mt-8 grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,28rem)] lg:gap-12">
          <div data-testid="sample-gap">
            <StatusPill tone="leak" label="Gap to segment win point" icon={StatusIcons.leak} />
            <p className="pk-figure m-0 mt-2 text-coral">{moneyShort(HERO_EXCESS)}</p>
            <p className="pk-small m-0 mt-1 max-w-[52ch] text-muted">
              discount given beyond each segment&rsquo;s win point ({pct(HERO_EXCESS_PCT)} of booked
              value), across the synthetic 2,000-deal book
            </p>
          </div>
          <DecisionRecord />
        </div>
        <h3 className="pk-h3 m-0 mt-12">One discount exception, from request to outcome</h3>
        <p className="pk-body m-0 mt-2 max-w-[68ch] text-muted">
          The same synthetic deal, in four steps. Each step is what the record holds.
        </p>
        <div className="mt-8">
          <DecisionWalk record={RECORD} />
        </div>
        <div className="mt-16">
          <h3 className="pk-h3 m-0">The readout behind it</h3>
          <div className="mt-4">
            <DiagnosticPreview data={PREVIEW_DATA} />
          </div>
        </div>
      </Section>

      {/* 5. Roles: one record, three views. */}
      <Section band="canvas" labelledBy="roles-h">
        <Eyebrow>Who reads it</Eyebrow>
        <h2 id="roles-h" className="pk-h2 m-0 mt-2">
          One decision record, three views.
        </h2>
        <div className="mt-8">
          <WhatYouGet />
        </div>
      </Section>

      {/* 6. Boundary: stated once. */}
      <Section band="band" labelledBy="boundary-h">
        <Eyebrow>Where the engine draws the line</Eyebrow>
        <h2 id="boundary-h" className="pk-h2 m-0 mt-2">
          What it will and will not do.
        </h2>
        <div className="mt-8">
          <TrustBoundaryStrip />
        </div>
      </Section>

      {/* 7. Close. */}
      <Section band="spotlight" labelledBy="close-h" width="prose" className="text-center">
        <Eyebrow>Start a conversation</Eyebrow>
        <h2 id="close-h" className="pk-h2 m-0 mt-2">
          Start with the audit, or with a conversation.
        </h2>
        <p className="pk-body m-0 mx-auto mt-3 max-w-[56ch]">
          No data or system access is needed to talk. Tell us how you price today and where the
          bill surprises you.
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-3">
          <Button href="/audit" size="lg">
            See the 14-day audit
          </Button>
          <Button href="/contact" variant="quiet">
            Talk to us &rarr;
          </Button>
        </div>
      </Section>
    </main>
  );
}
