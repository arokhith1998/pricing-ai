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
