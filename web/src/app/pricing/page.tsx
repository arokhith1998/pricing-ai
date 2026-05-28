import Link from "next/link";
import type { Metadata } from "next";
import Reveal from "@/components/Reveal";

export const dynamic = "force-static";
export const metadata: Metadata = { title: "Pricing · Pricekeel" };

// Optional: lead-form / outreach contact email is wired via this env var
// (same one the access-code page uses for the NDA mailto).
const CONTACT = process.env.NEXT_PUBLIC_CONTACT_EMAIL;

type Tier = {
  name: string;
  audience: string;
  body: string;
  features: string[];
  highlight?: boolean;
};

const TIERS: Tier[] = [
  {
    name: "Diagnostic",
    audience: "First touch / pilot",
    body:
      "A one-time retrospective on your closed deals. The full diagnostic + per-deal Guidance on the dataset you send. Under NDA if you need one.",
    features: [
      "CSV / Excel upload, mapping reviewed locally",
      "Win point + leakage lenses + packaging signal + trade-or-give",
      "Per-deal discount Guidance with plain-language factors",
      "Executive summary written from the figures",
    ],
  },
  {
    name: "Pricekeel Operate",
    audience: "Recurring engagement",
    body:
      "Diagnostic + Guidance, refreshed on every new quarter of deals. Ask-your-Pricekeel on your team's actual policy and playbook docs. Lightweight Slack share-outs to the deal desk.",
    features: [
      "Quarterly refresh of the full diagnostic",
      "Guidance available on the deals you're quoting now",
      "RAG chat trained on your policy / playbook / decks",
      "Email digests of new leakage and trade-or-give signals",
    ],
    highlight: true,
  },
  {
    name: "Margin Enhancement",
    audience: "Final phase",
    body:
      "The Phase 3 contract / margin layer. Connect Salesforce or HubSpot + Stripe or Zuora; we read active contracts, special pricing agreements, and renewal terms. Margin gaps across the whole book, not just closed deals.",
    features: [
      "Native CRM + billing connectors (CSV today)",
      "Active-contract analysis: SPAs, fixed discounts, renewal uplift gaps",
      "Renewal / expansion / contraction metrics",
      "Peer benchmarks once the base supports it",
    ],
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
      <a
        href={
          CONTACT
            ? `mailto:${CONTACT}?subject=Pricekeel%20${encodeURIComponent(tier.name)}`
            : "/upload"
        }
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
            We sell into pricing teams at $10–100M ARR B2B SaaS — that means an
            actual scoping call, not a self-serve checkout. Pick the closest fit
            and we will reply within one business day.
          </p>
          <p className="mx-auto mt-2 max-w-2xl text-sm text-muted">
            Engagements typically start in the low five figures; we share the
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

      <Reveal delay={0.05}>
        <section className="mt-12 rounded-xl border border-mist bg-surface p-6">
          <h2 className="text-lg font-semibold text-fg">
            Why we are not a feature inside a bigger tool
          </h2>
          <p className="mt-1 text-sm text-muted">
            A fair pushback in any first call. Three honest reasons we sit
            apart from RevOps / sales-intel / CPQ.
          </p>
          <ul className="mt-4 grid grid-cols-1 gap-4 text-sm md:grid-cols-3">
            <li className="rounded-lg border border-mist bg-surface-2 p-4">
              <div className="font-medium text-fg">
                Every decision is logged with its math
              </div>
              <p className="mt-1 text-muted">
                Defensible to finance. A CPQ field cannot tell a CFO why an
                approval went through; our diagnostic is open code, not a black
                box.
              </p>
            </li>
            <li className="rounded-lg border border-mist bg-surface-2 p-4">
              <div className="font-medium text-fg">
                Deterministic and auditable methodology
              </div>
              <p className="mt-1 text-muted">
                Same data, same answer, every time. An LLM-driven RevOps tool
                cannot promise that — and a CRO will not stake a deal-desk
                decision on output that drifts.
              </p>
            </li>
            <li className="rounded-lg border border-mist bg-surface-2 p-4">
              <div className="font-medium text-fg">
                Margin layer is a different data model
              </div>
              <p className="mt-1 text-muted">
                Active contracts, special pricing agreements, renewal terms —
                that lives in your billing system, not your CRM. Different
                schema, different metrics, different product.
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
                under NDA. Numbers come from your own CSV; the methodology is
                grounded in published pricing literature (Simon-Kucher
                discount governance, Nagle on reference price, Rivera on
                packaging architecture) and every metric is reproducible code
                you can audit. Customer logos and ROI cases follow design
                partner work, not the other way around.
              </p>
            </div>
            <div>
              <div className="font-medium text-fg">
                How does this integrate with our existing systems?
              </div>
              <p className="mt-1 text-muted">
                Today: a CSV or Excel export of closed deals from any CRM, and
                an XLSX / PDF / DOCX / PPTX of any pricing policy or playbook
                doc you want our chat to ground its answers in. Tomorrow
                (Phase 3, "Margin Enhancement"): native connectors for
                Salesforce, HubSpot, Stripe, Zuora, Snowflake.
              </p>
            </div>
            <div>
              <div className="font-medium text-fg">
                What are the security and compliance measures?
              </div>
              <p className="mt-1 text-muted">
                Row-level deal data is processed in memory and deleted —
                never written to disk and never sent to a cloud LLM. The cloud
                LLM only ever sees aggregate figures, column header names,
                document chunks you upload, and your question, all under
                zero-retention provider terms. Full details on{" "}
                <a href="/privacy" className="text-teal underline">
                  our privacy page
                </a>{" "}
                (final review by counsel pending).
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
              <span className="font-medium text-fg">Diagnostic</span> is a fixed
              one-time engagement — a few hours of your time to send the export
              and review the read-out together.
            </li>
            <li>
              <span className="font-medium text-fg">Pricekeel Operate</span> is
              an annual contract; ACV scales with deal volume and the number of
              policy docs we index.
            </li>
            <li>
              <span className="font-medium text-fg">Margin Enhancement</span> is
              custom — connector scope, contract data shape, and benchmark
              participation drive the number.
            </li>
          </ul>
        </section>
      </Reveal>
    </main>
  );
}
