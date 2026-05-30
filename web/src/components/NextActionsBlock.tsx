// Closing block on /diagnostic — answers the third CFO question from the
// 2026-05-30 expert review: "What decision will I make differently after
// the readout?"
//
// Three concrete next actions, each anchored to a number on the page.
// Not a generic "thanks for reading" — every line names a deal count or
// a dollar figure pulled from the analysis dict.

import type { Diagnostic } from "@/lib/api";

function fmtMoney(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

function fmtPct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

export default function NextActionsBlock({ analysis }: { analysis: Diagnostic }) {
  // defended_vs_investigate is required on Diagnostic since 2026-05-30; if a
  // cached pre-update API response is returned we still want to render
  // cleanly, so fall back to the leakage block.
  const dvi = analysis.defended_vs_investigate ?? {
    reference_threshold: analysis.leakage.reference_threshold,
    defended_value: 0,
    defended_deals: 0,
    investigate_value: analysis.leakage.excess_vs_reference_won,
    investigate_deals: analysis.leakage.deals_above_reference,
    defended_pct_of_booked: 0,
  };
  const lk = analysis.leakage;
  const gov = analysis.governance;

  const investigateDeals = dvi.investigate_deals;
  const investigateValue = dvi.investigate_value;
  const defendedDeals = dvi.defended_deals;
  const defendedValue = dvi.defended_value;
  const refThreshold = dvi.reference_threshold;
  const offPolicy = lk.off_policy_leakage_won;
  const noApprover = (gov as { off_policy_no_approver?: number }).off_policy_no_approver ?? 0;

  return (
    <section
      aria-label="What to do with this readout"
      className="rounded-2xl border border-mist bg-surface p-6"
    >
      <p className="text-xs font-semibold uppercase tracking-wider text-teal">
        What to do with this readout
      </p>
      <h2 className="mt-1 text-xl font-bold text-fg">
        Three actions a Head of Pricing can take this week
      </h2>
      <p className="mt-1 max-w-2xl text-sm text-muted">
        These are the moves the analysis above supports — each tied to a
        number on the page. Pricekeel is decision support, not autopilot;
        the call still belongs to your team.
      </p>

      <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-mist bg-surface-2 p-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-coral">
            1 · Investigate
          </div>
          <div className="mt-1 text-base font-bold text-fg">
            {investigateDeals.toLocaleString()} deals above the reference
          </div>
          <p className="mt-1 text-sm text-muted">
            Worth {fmtMoney(investigateValue)} of booked value. Walk the
            top of the deals-to-investigate list with the rep; ask what
            justified the discount and document the pattern.
          </p>
        </div>
        <div className="rounded-xl border border-teal/40 bg-surface-2 p-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-teal">
            2 · Defend the winners
          </div>
          <div className="mt-1 text-base font-bold text-fg">
            {defendedDeals.toLocaleString()} deals at or below {fmtPct(refThreshold)}
          </div>
          <p className="mt-1 text-sm text-muted">
            {fmtMoney(defendedValue)} of booked value where the discount
            plausibly earned the win. Tell sales: keep doing this. Resist
            blanket policy changes that punish disciplined discounting.
          </p>
        </div>
        <div className="rounded-xl border border-mist bg-surface-2 p-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-amber">
            3 · Tighten guardrails
          </div>
          <div className="mt-1 text-base font-bold text-fg">
            {fmtMoney(offPolicy)} given above policy
            {noApprover ? `, ${noApprover.toLocaleString()} with no approver` : ""}
          </div>
          <p className="mt-1 text-sm text-muted">
            Route every above-policy quote through deal desk. Set the
            approver field to required in your CRM. This is the lowest-
            friction guardrail with the highest expected effect.
          </p>
        </div>
      </div>

      <p className="mt-4 text-[11px] italic text-muted">
        Every figure here traces to a key in this analysis. Numbers are
        pricing upside to investigate, not guaranteed savings — see{" "}
        <a className="underline hover:text-fg" href="/trust">
          methodology
        </a>
        .
      </p>
    </section>
  );
}
