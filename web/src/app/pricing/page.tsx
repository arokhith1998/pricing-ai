import type { Metadata } from "next";
import Reveal from "@/components/Reveal";

export const dynamic = "force-static";
export const metadata: Metadata = { title: "Pricing · Pricekeel" };

type Tier = {
  name: string;
  audience: string;
  body: string;
  features: string[];
  highlight?: boolean;
  footer?: string;
};

// Tier copy is intentionally written so Diagnostic feels like the door-opener
// (free for design partners, one cycle) and Operate feels like the governance
// loop (requests priced, decisions logged, digests sent). The "Why Operate is
// a subscription" section below the cards makes the contrast visceral.
const TIERS: Tier[] = [
  {
    name: "Diagnostic",
    audience: "First touch, pilot",
    body:
      "A one-time retrospective on your last four quarters of closed deals. Free for design partners. Designed to prove the methodology on your own book before any commercial conversation.",
    features: [
      "CSV or Excel upload, mapping reviewed with you on the call",
      "Win point, leakage lenses, packaging signal, trade-or-give",
      "Per-deal discount Guidance with plain-language factors",
      "Executive summary written from the figures, CFO-forwardable",
    ],
    footer: "One cycle. NDA on request.",
  },
  {
    name: "Pricekeel Operate",
    audience: "The governance loop",
    body:
      "Not a report you read, a loop your deals run through. Every below-floor discount request is priced before it is approved, every decision lands in the log with its math, and the loop reports back to you on a weekly, monthly, and quarterly rhythm.",
    features: [
      "Every exception priced before it is approved: the floor, the win odds, the expected-value cost in dollars",
      "Every decision logged with its math, the audit trail your CFO and your next diligence see",
      "A weekly digest that comes to you: exceptions priced, below-floor count, realization, what moved",
      "Monthly drift readout naming the segments where realization is slipping and the deals behind it",
      "Quarterly policy re-simulation: floors re-fit against the deals you actually closed",
    ],
    highlight: true,
    footer:
      "Native Salesforce OAuth and live Opportunity analysis. Initial rollout remains founder-led.",
  },
  {
    name: "Data expansion",
    audience: "Explicitly deferred",
    body:
      "Billing/ERP cost data and product telemetry can eventually extend Pricekeel beyond CRM discount intelligence. They are separate data products and are not part of V1.",
    features: [
      "True margin only after a validated cost-data integration",
      "Application-level recommendations only after usage telemetry",
      "No blended CRM proxy presented as margin",
      "No build until the Salesforce workflow is validated",
    ],
    footer: "Roadmap context, not a product claim or current sales tier.",
  },
];

function TierCard({ tier }: { tier: Tier }) {
  return (
    <div
      className={`flex h-full flex-col rounded-2xl border p-6 shadow-sm ${
        tier.highlight
          ? "border-teal/50 bg-surface pk-upside-glow"
          : "border-mist bg-surface"
      }`}
    >
      <div className="text-xs font-semibold uppercase tracking-wider text-teal">
        {tier.audience}
      </div>
      <h2 className="mt-1 text-2xl font-bold text-fg">{tier.name}</h2>
      <p className="mt-2 text-sm text-muted">{tier.body}</p>
      <ul className="mt-4 flex-1 space-y-2 text-sm text-ink">
        {tier.features.map((f) => (
          <li key={f} className="flex gap-2">
            <span className="text-teal">✓</span>
            <span>{f}</span>
          </li>
        ))}
      </ul>
      {tier.footer ? (
        <p className="mt-4 text-xs italic text-muted">{tier.footer}</p>
      ) : null}
      <a
        href="/contact"
        className={`mt-6 block w-full rounded-lg px-4 py-3 text-center font-medium transition ${
          tier.highlight
            ? "bg-teal text-bg hover:scale-[1.01]"
            : "border border-mist bg-surface-2 text-fg hover:border-teal"
        }`}
      >
        Talk to us
      </a>
    </div>
  );
}

// Monday-morning scenarios for Operate. Answers the "why is this not just a
// repeat of the diagnostic" question by showing the concrete weekly artifacts
// a subscriber actually receives.
type Scenario = {
  when: string;
  who: string;
  what: string;
  detail: string;
};
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

// The economic case for the monthly invoice. Any one threshold cleared = renewal.
type Threshold = {
  label: string;
  math: string;
  who: string;
};
const THRESHOLDS: Threshold[] = [
  {
    label: "Deal-desk time recovered",
    math: "1 analyst, 5 hours per week saved, $80 per hour = ~$20K per year",
    who: "RevOps",
  },
  {
    label: "Caught underdiscounting",
    math:
      "1 to 2 deals per quarter where the rep would have given 3 to 5 extra points, at $250K ACV per deal = $30K to $50K per year saved",
    who: "Sales",
  },
  {
    label: "Board-defensible governance",
    math:
      "Decision log replaces a quarterly audit deck the VP of Pricing builds by hand. Worth the subscription at the $50M ARR tier on its own.",
    who: "Finance",
  },
];

export default function PricingPage() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <Reveal>
        <div className="text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-teal">
            Pricing
          </p>
          <h1 className="mt-2 text-3xl font-bold text-fg sm:text-4xl">
            Built for the conversation, not the credit card.
          </h1>
          <p className="mx-auto mt-3 max-w-2xl text-muted">
            We sell into pricing and RevOps teams at $20 to 100M ARR B2B SaaS. That means
            an actual scoping call, not a self-serve checkout. Pick the closest
            fit and we will reply within one business day.
          </p>
          <p className="mx-auto mt-2 max-w-2xl text-sm text-muted">
            Engagements typically start in the low five figures. We share the
            structure on the first call.
          </p>
        </div>
      </Reveal>

      <Reveal delay={0.05}>
        <div className="mt-10 grid grid-cols-1 gap-6 md:grid-cols-3">
          {TIERS.map((t) => (
            <TierCard key={t.name} tier={t} />
          ))}
        </div>
      </Reveal>

      {/* "Why monthly" answer block. The single most common pushback on a
          retrospective tool is "is this not just a one-time scan?" The Monday
          scenarios below answer it concretely. */}
      <Reveal delay={0.05}>
        <section className="mt-12 rounded-xl border border-teal/40 bg-surface p-6">
          <p className="text-xs font-semibold uppercase tracking-wider text-teal">
            Why Operate is a subscription
          </p>
          <h2 className="mt-1 text-xl font-bold text-fg">
            What a Monday looks like once you are on Operate.
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-muted">
            The Diagnostic is a one-page narrative your CFO reads once. Operate
            is the loop that runs after it: discount requests come through
            Pricekeel, decisions land in the log with their math, and the log
            reports back to you. Here is what that loop puts in your
            team&apos;s tools every week.
          </p>
          <ol className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
            {SCENARIOS.map((s, i) => (
              <li
                key={s.when}
                className="rounded-xl border border-mist bg-surface-2 p-5"
              >
                <div className="flex items-baseline gap-3">
                  <span className="text-xs font-bold tabular-nums text-teal">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate">
                    {s.when} · {s.who}
                  </div>
                </div>
                <div className="mt-1 text-base font-semibold text-fg">
                  {s.what}
                </div>
                <p className="mt-1 text-sm text-muted">{s.detail}</p>
              </li>
            ))}
          </ol>
          <p className="mt-5 text-xs italic text-muted">
            None of these scenarios fire from a one-time CSV scan. They fire
            because the loop is running: requests priced, decisions logged,
            digests sent. That is what justifies the subscription, not the
            diagnostic itself.
          </p>
        </section>
      </Reveal>

      {/* The economic case. Any one of three thresholds clears the renewal. */}
      <Reveal delay={0.05}>
        <section className="mt-8 rounded-xl border border-mist bg-surface p-6">
          <h2 className="text-lg font-semibold text-fg">
            What justifies the monthly invoice
          </h2>
          <p className="mt-1 text-sm text-muted">
            You only need to clear one of these three thresholds for Operate to
            pay for itself. Most subscribers will clear all three. You only need
            one to win the renewal conversation.
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wider text-slate">
                  <th className="pb-2 pr-4 font-semibold">Threshold</th>
                  <th className="pb-2 pr-4 font-semibold">Math</th>
                  <th className="pb-2 font-semibold">Who feels it</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-mist">
                {THRESHOLDS.map((t) => (
                  <tr key={t.label}>
                    <td className="py-3 pr-4 font-medium text-fg align-top">
                      {t.label}
                    </td>
                    <td className="py-3 pr-4 text-muted align-top">{t.math}</td>
                    <td className="py-3 text-slate align-top">{t.who}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </Reveal>

      <Reveal delay={0.05}>
        <section className="mt-8 rounded-xl border border-mist bg-surface p-6">
          <h2 className="text-lg font-semibold text-fg">
            Why we are not a feature inside a bigger tool
          </h2>
          <p className="mt-1 text-sm text-muted">
            A fair pushback in any first call. Three honest reasons we sit
            apart from RevOps, sales-intel, and CPQ.
          </p>
          <ul className="mt-4 grid grid-cols-1 gap-4 text-sm md:grid-cols-3">
            <li className="rounded-lg border border-mist bg-surface-2 p-4">
              <div className="font-medium text-fg">
                Every decision is logged with its math
              </div>
              <p className="mt-1 text-muted">
                Defensible to finance. A CPQ field cannot tell a CFO why an
                approval went through. Our diagnostic is open code, not a black
                box.
              </p>
            </li>
            <li className="rounded-lg border border-mist bg-surface-2 p-4">
              <div className="font-medium text-fg">
                Deterministic and auditable methodology
              </div>
              <p className="mt-1 text-muted">
                Same data, same answer, every time. An LLM-driven RevOps tool
                cannot promise that, and a CRO will not stake a deal-desk
                decision on output that drifts.
              </p>
            </li>
            <li className="rounded-lg border border-mist bg-surface-2 p-4">
              <div className="font-medium text-fg">
                CRM evidence has a hard boundary
              </div>
              <p className="mt-1 text-muted">
                Salesforce supports discount and outcome evidence. Cost-based
                margin needs billing or ERP; application guidance needs usage
                telemetry. We label those gaps instead of manufacturing proxies.
              </p>
            </li>
          </ul>
        </section>
      </Reveal>

      <Reveal delay={0.05}>
        <section className="mt-8 rounded-xl border border-mist bg-surface p-6">
          <h2 className="text-lg font-semibold text-fg">
            What CFOs ask in the first ten minutes
          </h2>
          <div className="mt-4 space-y-5 text-sm">
            <div>
              <div className="font-medium text-fg">
                What is the proven ROI from existing customers?
              </div>
              <p className="mt-1 text-muted">
                We are in design-partner mode. The first diagnostic is free and
                under NDA. Numbers come from your own CSV. The methodology is
                grounded in published pricing literature (Simon-Kucher discount
                governance, Nagle on reference price, Rivera on packaging
                architecture) and every metric is reproducible code you can
                audit. Customer logos and ROI cases follow design partner work,
                not the other way around.
              </p>
            </div>
            <div>
              <div className="font-medium text-fg">
                How does this integrate with our existing systems?
              </div>
              <p className="mt-1 text-muted">
                Salesforce connects through real OAuth. Pricekeel reads live
                Opportunity history, discovers your fields, applies an explicit
                mapping, and returns the executive, Pricing/RevOps, and deal-desk
                views. CSV or Excel remains the diagnostic/onboarding path for
                other CRMs; billing and telemetry connectors are not in V1.
              </p>
            </div>
            <div>
              <div className="font-medium text-fg">
                What are the security and compliance measures?
              </div>
              <p className="mt-1 text-muted">
                Salesforce tokens are server-side and encrypted at rest. Live
                Opportunity rows are processed through the protected pricing
                service and are not persisted in Pricekeel&apos;s database or sent
                to a cloud LLM. Decision events and derived evidence are stored
                so the audit trail survives. Full details on{" "}
                <a href="/privacy" className="text-teal underline">
                  our privacy page
                </a>
                .
              </p>
            </div>
          </div>
        </section>
      </Reveal>

      <Reveal delay={0.05}>
        <section className="mt-8 rounded-xl border border-mist bg-surface p-6">
          <h2 className="text-lg font-semibold text-fg">How we scope it</h2>
          <ul className="mt-3 space-y-2 text-sm text-muted">
            <li>
              <span className="font-medium text-fg">Diagnostic</span> is a
              fixed one-time engagement. A few hours of your time to send the
              export and review the read-out together. Free for design partners.
            </li>
            <li>
              <span className="font-medium text-fg">Pricekeel Operate</span>{" "}
              is a Salesforce-native exception loop: live Opportunity analysis,
              field mapping, recommendations, accept/override, approval, audit
              log, and optional Salesforce Task writeback. The initial rollout
              is founder-led; engagements typically start in the low five figures.
            </li>
            <li>
              <span className="font-medium text-fg">Data expansion</span> is not
              sold as V1. Billing/ERP and product-telemetry work requires its own
              validated data contract and design decision.
            </li>
          </ul>
        </section>
      </Reveal>
    </main>
  );
}
