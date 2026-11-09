import Link from "next/link";
import { Button, Card, Eyebrow, PageHeader, Section, SyntheticTag } from "@/components/ui";
import { pageMetadata } from "@/lib/page-metadata";

export const dynamic = "force-static";
export const metadata = pageMetadata({
  title: "Pricing",
  description:
    "Two ways to work with Pricekeel: a one-time Diagnostic on your closed deals, and Operate, the Salesforce discount-exception loop. Scoped on a call.",
  path: "/pricing",
});

type Tier = {
  id: string;
  name: string;
  audience: string;
  body: string;
  features: string[];
  footer: string;
  primary?: boolean;
};

const TIERS: Tier[] = [
  {
    id: "diagnostic",
    name: "Diagnostic",
    audience: "First touch, pilot",
    body: "A one-time retrospective on your last four quarters of closed deals. Free for design partners. Designed to prove the methodology on your own book before any commercial conversation.",
    features: [
      "CSV or Excel upload, mapping reviewed with you on the call",
      "Win point, leakage lenses, packaging signal, trade-or-give",
      "Per-deal discount Guidance with plain-language factors",
      "Executive summary written from the figures, CFO-forwardable",
    ],
    footer: "One cycle. NDA on request.",
  },
  {
    id: "operate",
    name: "Pricekeel Operate",
    audience: "The governance loop",
    body: "Not a report you read, a loop your deals run through. Every below-floor discount request is priced before it is approved, every decision lands in the log with its math, and the loop reports back to you on a weekly, monthly, and quarterly rhythm.",
    features: [
      "Every exception priced before it is approved: the floor, the win odds, the expected-value cost in dollars",
      "Every decision logged with its math, the audit trail your CFO and your next diligence see",
      "A weekly digest that comes to you: exceptions priced, below-floor count, realization, what moved",
      "Monthly drift readout naming the segments where realization is slipping and the deals behind it",
      "Quarterly policy re-simulation: floors re-fit against the deals you actually closed",
    ],
    footer: "Native Salesforce OAuth and live Opportunity analysis. Initial rollout remains founder-led.",
    primary: true,
  },
];

function TierCard({ tier }: { tier: Tier }) {
  return (
    <li data-tier={tier.id} className="flex">
      <Card as="article" className="flex w-full flex-col p-6 sm:p-8">
        <Eyebrow>{tier.audience}</Eyebrow>
        <h2 className="pk-h2 mt-2">{tier.name}</h2>
        <p className="pk-body mt-3 text-muted">{tier.body}</p>
        <ul className="pk-body mt-5 flex-1 list-disc space-y-3 pl-5 text-ink marker:text-teal">
          {tier.features.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
        <p className="pk-small mt-6 text-muted">{tier.footer}</p>
        <Button
          href="/contact"
          variant={tier.primary ? "primary" : "secondary"}
          size="lg"
          className="mt-6 w-full"
        >
          Talk to us
        </Button>
      </Card>
    </li>
  );
}

// Monday-morning scenarios for Operate. The figures are hand-built, not read
// from the snapshot, so each card carries the "Illustrative, not customer data"
// label.
type Scenario = { when: string; who: string; what: string; detail: string };
const SCENARIOS: Scenario[] = [
  {
    when: "Monday, 8:30 AM",
    who: "Pricing workspace",
    what: "Live Salesforce refresh shows three opportunities above guardrail",
    detail:
      "Largest: $480K Enterprise at 22%. The disclosed segment reference is 14%, with the historical band counts and closest won/lost deals attached.",
  },
  {
    when: "Monday, 9:15 AM",
    who: "Executive view",
    what: "CFO sees realization, win rate, exceptions, and price to retain",
    detail:
      "Every figure comes from the connected Opportunity history. Sparse cohorts and missing list values are shown as readiness warnings, not hidden.",
  },
  {
    when: "Wednesday, 4:00 PM",
    who: "Rep in Pricekeel deal desk",
    what: "Recommendation and override before approval",
    detail:
      "Accept the recommendation or request an override with justification. The action is appended to the decision log and can write a completed Task back to the Salesforce Opportunity.",
  },
  {
    when: "End of quarter",
    who: "CFO before the board prep",
    what: "Defended-vs-investigate dashboard, updated weekly",
    detail:
      "What discipline earned the quarter, what to investigate next, and every approval or rejection traceable to its historical evidence and actor.",
  },
];

// The reader's own assumptions, not results. Each row is a placeholder to
// replace with the reader's numbers.
type Threshold = { label: string; math: string; who: string };
const THRESHOLDS: Threshold[] = [
  {
    label: "Deal-desk time recovered",
    math: "If 1 analyst saves 5 hours per week at $80 per hour, that is about $20K per year.",
    who: "RevOps",
  },
  {
    label: "Caught underdiscounting",
    math: "If 1 to 2 deals per quarter would have had 3 to 5 extra points given, at $250K ACV per deal, that is $30K to $50K per year.",
    who: "Sales",
  },
  {
    label: "Board-defensible governance",
    math: "If the decision log replaces a quarterly audit deck the VP of Pricing builds by hand, count those hours at your own rate.",
    who: "Finance",
  },
];

export default function PricingPage() {
  return (
    <main id="main" tabIndex={-1}>
      <Section>
        <PageHeader
          eyebrow="Pricing"
          title="Built for the conversation, not the credit card."
          lead="We sell into pricing and RevOps teams at $10M to $100M ARR B2B SaaS. That means an actual scoping call, not a self-serve checkout. Pick the closest fit and we will reply within one business day."
        />
        <p className="pk-body mt-4 max-w-prose text-muted">
          We expect pricing to start in the low five figures. We share the structure on the first
          call.
        </p>
        <ul className="mt-10 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {TIERS.map((t) => (
            <TierCard key={t.id} tier={t} />
          ))}
        </ul>
        <p
          data-roadmap="data-expansion"
          className="pk-body mt-8 max-w-prose border-l-2 border-control pl-4 text-muted"
        >
          <span className="font-medium text-fg">On the roadmap, not for sale: data expansion.</span>{" "}
          Billing/ERP cost data and product telemetry can eventually extend Pricekeel beyond CRM
          discount intelligence. They are separate data products and are not part of V1. True margin
          only after a validated cost-data integration; no blended CRM proxy is ever presented as
          margin.
        </p>
      </Section>

      <Section band="band" labelledBy="monday-title">
        <Eyebrow>Why Operate is a subscription</Eyebrow>
        <h2 id="monday-title" className="pk-h2 mt-2">
          What a Monday looks like once you are on Operate.
        </h2>
        <p className="pk-body mt-3 max-w-prose text-muted">
          The Diagnostic is a one-page narrative your CFO reads once. Operate is the loop that runs
          after it: discount requests come through Pricekeel, decisions land in the log with their
          math, and the log reports back to you. Here is what that loop puts in your team&apos;s
          tools every week.
        </p>
        <ol className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2">
          {SCENARIOS.map((s, i) => (
            <li key={s.when} data-scenario className="flex">
              <Card tone="inset" className="w-full">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                  <span className="pk-small font-semibold tabular-nums text-teal">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="pk-small text-muted">
                    {s.when}, {s.who}
                  </span>
                  <SyntheticTag variant="illustrative" />
                </div>
                <h3 className="pk-h3 mt-3">{s.what}</h3>
                <p className="pk-body mt-2 text-muted">{s.detail}</p>
              </Card>
            </li>
          ))}
        </ol>
        <p className="pk-body mt-6 max-w-prose text-muted">
          None of these scenarios fire from a one-time CSV scan. They fire because the loop is
          running: requests priced, decisions logged, digests sent.
        </p>
      </Section>

      <Section labelledBy="roi-title">
        <Eyebrow>Your numbers</Eyebrow>
        <h2 id="roi-title" className="pk-h2 mt-2">
          Test the monthly invoice against your own assumptions.
        </h2>
        <p className="pk-body mt-3 max-w-prose text-muted">
          These three thresholds use placeholder assumptions. They are not results from any customer.
          Replace each with your own figures; if none of them holds for your team, Operate is not
          worth buying.
        </p>
        <ul className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
          {THRESHOLDS.map((t) => (
            <li key={t.label} data-threshold className="flex">
              <Card className="w-full">
                <SyntheticTag variant="illustrative" />
                <p className="pk-small mt-3 text-muted">Placeholder assumption, replace with yours</p>
                <h3 className="pk-h3 mt-1">{t.label}</h3>
                <p className="pk-body mt-2 text-muted">{t.math}</p>
                <p className="pk-small mt-3 text-slate">Who feels it: {t.who}</p>
              </Card>
            </li>
          ))}
        </ul>
      </Section>

      <Section band="band" labelledBy="apart-title">
        <h2 id="apart-title" className="pk-h2">
          Why we are not a feature inside a bigger tool
        </h2>
        <p className="pk-body mt-3 max-w-prose text-muted">
          A fair pushback in any first call. Three honest reasons we sit apart from RevOps,
          sales-intel, and CPQ.
        </p>
        <ul className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
          <li className="flex">
            <Card tone="inset" className="w-full">
              <h3 className="pk-h3">Every decision is logged with its math</h3>
              <p className="pk-body mt-2 text-muted">
                Defensible to finance. A CPQ field cannot tell a CFO why an approval went through.
                Our method is documented, not a black box.
              </p>
            </Card>
          </li>
          <li className="flex">
            <Card tone="inset" className="w-full">
              <h3 className="pk-h3">Deterministic and auditable methodology</h3>
              <p className="pk-body mt-2 text-muted">
                Same data, same answer, every time. An LLM-driven RevOps tool cannot promise that,
                and a CRO will not stake a deal-desk decision on output that drifts.
              </p>
            </Card>
          </li>
          <li className="flex">
            <Card tone="inset" className="w-full">
              <h3 className="pk-h3">CRM evidence has a hard boundary</h3>
              <p className="pk-body mt-2 text-muted">
                Salesforce supports discount and outcome evidence. Cost-based margin needs billing
                or ERP; application guidance needs usage telemetry. We label those gaps instead of
                manufacturing proxies.
              </p>
            </Card>
          </li>
        </ul>
      </Section>

      <Section labelledBy="faq-title">
        <h2 id="faq-title" className="pk-h2">
          What CFOs ask in the first ten minutes
        </h2>
        <div className="mt-8 max-w-prose space-y-8">
          <div>
            <h3 className="pk-h3">What is the proven ROI from existing customers?</h3>
            <p className="pk-body mt-2 text-muted">
              We are in design-partner mode. The first diagnostic is free and under NDA. Numbers come
              from your own CSV. The methodology is grounded in published pricing literature
              (Simon-Kucher discount governance, Nagle on reference price, Rivera on packaging
              architecture) and the code behind every metric can be audited under NDA. Customer logos
              and ROI cases follow design partner work, not the other way around.
            </p>
          </div>
          <div>
            <h3 className="pk-h3">How does this integrate with our existing systems?</h3>
            <p className="pk-body mt-2 text-muted">
              Salesforce connects through real OAuth. Pricekeel reads live Opportunity history,
              discovers your fields, applies an explicit mapping, and returns the executive,
              Pricing/RevOps, and deal-desk views. CSV or Excel remains the diagnostic/onboarding path
              for other CRMs; billing and telemetry connectors are not in V1.
            </p>
          </div>
          <div>
            <h3 className="pk-h3">What are the security and compliance measures?</h3>
            <p className="pk-body mt-2 text-muted">
              Salesforce tokens are server-side and encrypted at rest. Live Opportunity rows are
              processed through the protected pricing service and are not persisted in
              Pricekeel&apos;s database or sent to a cloud LLM. Decision events and derived evidence
              are stored so the audit trail survives. Full details on{" "}
              <Link href="/privacy" className="text-teal underline underline-offset-4">
                our privacy page
              </Link>
              .
            </p>
          </div>
        </div>
      </Section>

      <Section band="band" labelledBy="scope-title">
        <h2 id="scope-title" className="pk-h2">
          How we scope it
        </h2>
        <ul className="pk-body mt-6 max-w-prose space-y-4 text-muted">
          <li>
            <span className="font-medium text-fg">Diagnostic</span> is a fixed one-time engagement. A
            few hours of your time to send the export and review the read-out together. Free for
            design partners.
          </li>
          <li>
            <span className="font-medium text-fg">Pricekeel Operate</span> is a Salesforce-native
            exception loop: live Opportunity analysis, field mapping, recommendations,
            accept/override, approval, audit log, and optional Salesforce Task writeback. The initial
            rollout is founder-led. We expect pricing to start in the low five figures.
          </li>
          <li>
            <span className="font-medium text-fg">Data expansion</span> is not sold as V1.
            Billing/ERP and product-telemetry work requires its own validated data contract and
            design decision.
          </li>
        </ul>
        <div className="mt-8">
          <Button href="/contact" size="lg">
            Talk to us
          </Button>
        </div>
      </Section>
    </main>
  );
}
