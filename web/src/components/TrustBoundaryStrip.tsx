// Section 4 of the landing page: one strip that states the engine's
// boundaries once each, then folds methodology, founder credential, and
// trust-page links into a single compact row instead of three separate
// credibility sections. Replaces FounderStrip, TrustStrip, and
// MethodologyStrip (moved to /methodology) as landing-page content.
import Link from "next/link";

const METHOD_AUTHORS = ["Nagle", "Ramanujam", "Bertini", "Simon-Kucher", "Rivera"];

export default function TrustBoundaryStrip() {
  return (
    <section
      aria-label="What the engine will and will not tell you"
      className="rounded-2xl border border-mist bg-surface px-6 py-6"
    >
      <p className="text-xs font-semibold uppercase tracking-wider text-teal">
        Where the engine draws the line
      </p>
      <ul className="mt-3 space-y-2 text-sm leading-6 text-fg">
        <li>
          Every recommendation says whether it is a modeled optimum or a support floor.
        </li>
        <li>Too thin a book and it says insufficient data instead of a number.</li>
        <li>
          V1 governs the discount on committed ACV. Commit, ramp and overage
          are captured, not yet scored.
        </li>
        <li>Row-level deal data is processed in memory and deleted.</li>
      </ul>
      <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-mist pt-3 text-xs text-muted">
        <span>Method: {METHOD_AUTHORS.join(" · ")}.</span>
        <span>Built by Adhithya Bhaskar, Simon Business School.</span>
        <Link href="/trust" className="font-medium text-teal hover:underline">
          Trust
        </Link>
        <Link href="/methodology" className="font-medium text-teal hover:underline">
          Methodology
        </Link>
      </div>
    </section>
  );
}
