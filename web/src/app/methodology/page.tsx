// Diligence-grade bibliography, moved off the landing page (which now links
// here from its trust-and-boundary strip) so the credibility anchor still
// exists without adding a fourth credibility section to the scroll.
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Methodology · Pricekeel" };
export const dynamic = "force-static";

type Source = {
  author: string;
  work: string;
  contribution: string;
  url: string;
};

const SOURCES: Source[] = [
  {
    author: "Thomas Nagle",
    work: "Strategy & Tactics of Pricing",
    contribution: "Reference price, value-based pricing, EVC",
    url: "https://www.routledge.com/The-Strategy-and-Tactics-of-Pricing-A-Guide-to-Growing-More-Profitably/Nagle-Muller/p/book/9781032016078",
  },
  {
    author: "Simon-Kucher",
    work: "Deal Desk & Discount Governance Practice",
    contribution: "Discount governance, approval routing, packaging",
    url: "https://www.simon-kucher.com/en",
  },
  {
    author: "Madhavan Ramanujam",
    work: "Monetizing Innovation",
    contribution: "Pricing fences, value-metric fit, willingness-to-pay",
    url: "https://www.simon-kucher.com/en/insights/monetizing-innovation",
  },
  {
    author: "Marco Bertini",
    work: "The Ends Game",
    contribution: "Outcome-based pricing, subscription transformation",
    url: "https://mitpress.mit.edu/9780262539968/the-ends-game/",
  },
  {
    author: "Marcos Rivera",
    work: "Street Pricing (Pricing I/O)",
    contribution: "Packaging signal, pricing-page architecture",
    url: "https://www.amazon.com/Street-Pricing-Playlist-Leaders-SaaS/dp/1737528010",
  },
];

function Card({ s }: { s: Source }) {
  return (
    <a
      href={s.url}
      target="_blank"
      rel="noreferrer noopener"
      className="group block rounded-xl border border-mist bg-surface p-4 transition hover:border-teal hover:shadow-sm"
    >
      <div className="text-xs font-semibold uppercase tracking-wider text-teal">{s.author}</div>
      <div className="mt-1 text-sm font-medium text-fg group-hover:text-teal">{s.work}</div>
      <div className="mt-1 text-xs text-muted">{s.contribution}</div>
    </a>
  );
}

export default function MethodologyPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-bold text-fg">Methodology</h1>
      <p className="mt-4 text-sm leading-relaxed text-muted">
        Every signal in the Pricekeel decision record, the leakage lens, win
        point, packaging signal, and trade-or-give, is grounded in a
        published framework, not invented math. This is the bibliography a
        Head of Pricing can cite when defending a discount approval.
      </p>
      <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {SOURCES.map((s) => (
          <Card key={s.author} s={s} />
        ))}
      </div>
      <p className="mt-8 text-sm">
        <Link href="/" className="font-medium text-teal hover:underline">
          &larr; Back to Pricekeel
        </Link>
      </p>
    </main>
  );
}
