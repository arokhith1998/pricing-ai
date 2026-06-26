import { Stagger, StaggerItem } from "@/components/Reveal";

// Merged "what it does" capabilities + "what you get" deliverables. Each row is
// one pillar: the capability on the left, the concrete artifact it produces on
// the right. Consolidated from the former separate "What it does" cards and
// DeliverableSection so the four pillars are stated once, not twice (the page
// was re-treading the same four ideas across two grids).
const PILLARS: { pillar: string; does: string; artifact: string; get: string }[] = [
  {
    pillar: "Find the leakage",
    does:
      "Price realization, win rate by discount band, and three views of discount leakage, from a plain description to the strongest claim worth acting on.",
    artifact: "Executive summary",
    get:
      "A one-page narrative your CFO reads in two minutes: booked value, price realization, win point, the headline upside, and the top three deals to investigate. Plain English, no jargon.",
  },
  {
    pillar: "Find the win point",
    does:
      "The discount level where win rate stops improving. Everything given beyond it is a list to investigate, not a refund.",
    artifact: "Win-curve report",
    get:
      "Win rate by discount band with the calculated reference point, the band where bigger discounts stop buying wins. The chart your Head of Pricing forwards to the CRO.",
  },
  {
    pillar: "Guide the next discount",
    does:
      "A win-probability model recommends the discount that maximizes expected value on a given deal, with a plain-language why.",
    artifact: "Per-deal guidance",
    get:
      "For each open opportunity: recommended discount, expected-value lift, win-probability change, and the top three factors the model thinks drive the deal. Decision support for the deal-desk call.",
  },
  {
    pillar: "Defend the decision",
    does:
      "Every recommendation is logged with the math behind it. The Copilot answers CFO questions with citations to the source signal, with no LLM-invented numbers.",
    artifact: "Defended-vs-investigate list",
    get:
      "Won deals split into 'discount earned the win' (defend in sales review) and 'discount worth a retrospective look' (route to deal-desk debrief). Sales-friendly framing of the same data.",
  },
];

export default function WhatYouGet() {
  return (
    <section aria-label="What it does and what you walk away with">
      <div className="text-center">
        <p className="text-xs font-semibold uppercase tracking-wider text-teal">
          What it does · what you walk away with
        </p>
        <h2 className="mt-2 text-xl font-bold text-fg sm:text-2xl">
          Four answers, four artifacts you can forward unchanged
        </h2>
        <p className="mx-auto mt-2 max-w-2xl text-sm text-muted">
          Each pillar produces a deliverable a Head of Pricing forwards to the
          CFO as-is. No dashboard to interpret, no copy-paste cleanup.
        </p>
      </div>

      <Stagger className="mt-6 grid grid-cols-1 gap-3">
        {PILLARS.map((p, i) => (
          <StaggerItem key={p.pillar}>
            <div className="grid grid-cols-1 gap-4 rounded-xl border border-mist bg-surface p-5 md:grid-cols-[1fr_auto_1.1fr] md:items-center md:gap-5">
              {/* Capability: what it does */}
              <div>
                <div className="flex items-baseline gap-2">
                  <span className="text-xs font-bold tabular-nums text-teal">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <h3 className="text-base font-semibold text-fg">{p.pillar}</h3>
                </div>
                <p className="mt-1 text-sm text-slate">{p.does}</p>
              </div>

              {/* Connector (desktop only) */}
              <div
                aria-hidden
                className="hidden md:block md:h-full md:border-l md:border-mist"
              />

              {/* Deliverable: what you get */}
              <div className="rounded-lg border border-mist bg-surface-2 p-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-teal">
                  You get · {p.artifact}
                </p>
                <p className="mt-1 text-sm text-muted">{p.get}</p>
              </div>
            </div>
          </StaggerItem>
        ))}
      </Stagger>
    </section>
  );
}
