import type { Metadata } from "next";
import { Button, Eyebrow, Section } from "@/components/ui";
import HeroHeadline from "@/components/HeroHeadline";
import Bottlenecks from "@/components/landing/Bottlenecks";
import { pageMetadata } from "@/lib/page-metadata";
import { AUDIT_DAYS, AUDIT_PRICE, COST_BASIS_LABEL } from "@/lib/audit-offer";

// Static marketing landing. No API dependency, so it always loads fast.
export const dynamic = "force-static";

// F15 and ADR-008: the page says only what the two research-sheet tabs say,
// in this order: the line, who it is for, the six bottlenecks, the offer in
// three lines with one call to action. Nothing else.
export const metadata: Metadata = pageMetadata({
  title: "A 14-day pricing audit for AI companies",
  description:
    "We stop AI companies from losing money on heavy users. For B2B and AI software companies moving from flat or per-seat to usage or outcome pricing.",
  path: "/",
});

export default function Landing() {
  return (
    <main id="main" tabIndex={-1} className="outline-none">
      <Section band="canvas" labelledBy="hero-h">
        <HeroHeadline />
        <p className="pk-lead m-0 mt-4 max-w-[56ch]" data-testid="audience">
          For B2B and AI software companies moving from flat or per-seat to usage or outcome
          pricing.
        </p>
      </Section>

      <Section band="band" labelledBy="bottlenecks-h">
        <Eyebrow>The AI pricing bottleneck</Eyebrow>
        <h2 id="bottlenecks-h" className="pk-h2 m-0 mt-2">
          Where AI pricing breaks.
        </h2>
        <div className="mt-6">
          <Bottlenecks />
        </div>
      </Section>

      <Section band="canvas" labelledBy="offer-h">
        <Eyebrow>The offer</Eyebrow>
        <h2 id="offer-h" className="pk-h2 m-0 mt-2">
          A {AUDIT_DAYS}-day pricing audit.
        </h2>
        <ul className="pk-body m-0 mt-4 max-w-[68ch] list-none space-y-2 p-0 text-muted" data-testid="offer">
          <li>
            A done-for-you audit of your billing and cost exports: which customers and plans cost
            more to serve than they pay, on {COST_BASIS_LABEL}, and a packaging structure for you
            to decide on.
          </li>
          <li>{AUDIT_DAYS} days from validated intake.</li>
          <li>{AUDIT_PRICE} fixed, paid upfront.</li>
        </ul>
        <div className="mt-6">
          <Button href="/audit" size="lg">
            See the 14-day audit
          </Button>
        </div>
      </Section>
    </main>
  );
}
