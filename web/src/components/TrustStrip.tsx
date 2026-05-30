// Compact pre-footer trust signal. Surfaces the legal-pack pages we just
// shipped (privacy, terms, subprocessors, trust) and reinforces the single
// most reassuring fact for a CFO buyer: row-level data does not leave the
// server in memory.

import Link from "next/link";

const LINKS: [string, string][] = [
  ["/privacy", "Privacy"],
  ["/terms", "Terms"],
  ["/subprocessors", "Subprocessors"],
  ["/trust", "Trust & Security"],
];

export default function TrustStrip() {
  return (
    <section
      aria-label="Trust and compliance"
      className="rounded-xl border border-mist bg-surface px-5 py-4 sm:flex sm:items-center sm:justify-between sm:gap-4"
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden
          className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-teal/40 bg-surface-2 text-teal"
        >
          {/* shield-check icon, inline so no font dep */}
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            <path d="M9 12l2 2 4-4" />
          </svg>
        </span>
        <div>
          <div className="text-sm font-semibold text-fg">
            Row-level deal data is processed in memory and deleted
          </div>
          <p className="mt-0.5 text-xs text-muted">
            The cloud LLM sees only aggregate figures, column headers, document
            chunks you upload, and your questions. Never row-level data, and
            always under zero-retention provider terms.
          </p>
        </div>
      </div>
      <nav className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted sm:mt-0 sm:shrink-0">
        {LINKS.map(([href, label]) => (
          <Link key={href} href={href} className="hover:text-fg">
            {label}
          </Link>
        ))}
      </nav>
    </section>
  );
}
