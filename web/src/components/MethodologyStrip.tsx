// Methodology credibility strip — the five frameworks the diagnostic and
// the recommendation engine are grounded in. Pre-customer, this is the
// strongest credibility anchor we have: "we did not invent the math; we
// built a defensible decision system on top of it."
//
// When real customer logos exist, this stays — methodology grounding is
// permanent positioning, not a placeholder.

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
    contribution: "Reference price · value-based pricing · EVC",
    url: "https://www.routledge.com/The-Strategy-and-Tactics-of-Pricing-A-Guide-to-Growing-More-Profitably/Nagle-Muller/p/book/9781032016078",
  },
  {
    author: "Simon-Kucher",
    work: "Confessions of the Pricing Man (Hermann Simon)",
    contribution: "Discount governance · approval routing · packaging",
    url: "https://www.simon-kucher.com/en",
  },
  {
    author: "Madhavan Ramanujam",
    work: "Monetizing Innovation",
    contribution: "Pricing fences · value-metric fit · willingness-to-pay",
    url: "https://www.simon-kucher.com/en/insights/monetizing-innovation",
  },
  {
    author: "Marco Bertini",
    work: "The Ends Game",
    contribution: "Outcome-based pricing · subscription transformation",
    url: "https://mitpress.mit.edu/9780262539968/the-ends-game/",
  },
  {
    author: "Manuel Rivera",
    work: "SaaS packaging architecture (OpenView · Kyle Poyar)",
    contribution: "Packaging signal · pricing-page architecture",
    url: "https://openviewpartners.com/blog/",
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
      <div className="text-xs font-semibold uppercase tracking-wider text-teal">
        {s.author}
      </div>
      <div className="mt-1 text-sm font-medium text-fg group-hover:text-teal">
        {s.work}
      </div>
      <div className="mt-1 text-xs text-muted">{s.contribution}</div>
    </a>
  );
}

export default function MethodologyStrip() {
  return (
    <section aria-label="Methodology credibility">
      <div className="text-center">
        <p className="text-xs font-semibold uppercase tracking-wider text-teal">
          Built on named methodology, not vibes
        </p>
        <h2 className="mt-2 text-xl font-bold text-fg sm:text-2xl">
          Defensible to finance because the math has authors
        </h2>
        <p className="mx-auto mt-2 max-w-2xl text-sm text-muted">
          Every Pricekeel signal — leakage lenses, win point, packaging signal,
          trade-or-give, decision log — is grounded in a published framework
          your Head of Pricing can cite when defending a discount approval.
        </p>
      </div>
      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {SOURCES.map((s) => (
          <Card key={s.author} s={s} />
        ))}
      </div>
    </section>
  );
}
