import { Stagger, StaggerItem } from "@/components/Reveal";

const ROLES = [
  {
    role: "Deal Desk + RevOps",
    moment: "Price the live exception",
    outcome:
      "See the requested discount beside the recommended guardrail, closest comparable deals, and the expected-value tradeoff. Accept, trade, or override without opening an analyst ticket.",
    measures: ["Exception cycle time", "Override rate", "Price retained"],
  },
  {
    role: "Pricing",
    moment: "Improve the guardrails",
    outcome:
      "Analyze realization and win rate by segment, product, customer, and discount band. Add cited competitor context, then trace every recommendation back to the evidence that produced it.",
    measures: ["Price realization", "Win rate by band", "Policy drift"],
  },
  {
    role: "Finance",
    moment: "Govern the value given away",
    outcome:
      "Track price realization, discounts above policy, retained value, and who approved each exception. Add billing or ERP cost data before calling any output true margin.",
    measures: ["Realization", "Above-policy value", "Audit coverage"],
  },
];

export default function WhatYouGet() {
  return (
    <section aria-label="Role-specific outcomes">
      <div className="text-center">
        <p className="text-xs font-semibold uppercase tracking-wider text-teal">
          One system, three operating views
        </p>
        <h2 className="mt-2 text-xl font-bold text-fg sm:text-2xl">
          Each buyer sees the decision at their altitude
        </h2>
        <p className="mx-auto mt-2 max-w-2xl text-sm text-muted">
          Reps do not need another dashboard. Pricing needs evidence. Finance
          needs control. Pricekeel gives each team a view of the same decision
          record instead of three versions of the truth.
        </p>
      </div>

      <Stagger className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        {ROLES.map((item) => (
          <StaggerItem key={item.role}>
            <div className="flex h-full flex-col rounded-xl border border-mist bg-surface p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-teal">{item.role}</p>
              <h3 className="mt-2 text-lg font-semibold text-fg">{item.moment}</h3>
              <p className="mt-2 flex-1 text-sm leading-6 text-muted">{item.outcome}</p>
              <div className="mt-5 flex flex-wrap gap-2 border-t border-mist pt-4">
                {item.measures.map((measure) => (
                  <span key={measure} className="rounded-full border border-mist bg-surface-2 px-2.5 py-1 text-xs font-medium text-slate">
                    {measure}
                  </span>
                ))}
              </div>
            </div>
          </StaggerItem>
        ))}
      </Stagger>
    </section>
  );
}
