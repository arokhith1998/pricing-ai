import { Stagger, StaggerItem } from "@/components/Reveal";

const ROLES: { role: string; line: string }[] = [
  {
    role: "Deal Desk",
    line: "See the guardrail and the closest comparable deals. Accept, trade, or override.",
  },
  {
    role: "Pricing",
    line: "See realization and win rate by segment and band, with cited competitor context.",
  },
  {
    role: "Finance",
    line: "See who approved what, and where CRM discount data stops and true margin needs billing or ERP.",
  },
];

export default function WhatYouGet() {
  return (
    <section aria-label="One decision record, three views">
      <h2 className="text-center text-xl font-bold text-fg sm:text-2xl">
        One decision record, three views.
      </h2>
      <Stagger className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {ROLES.map((item) => (
          <StaggerItem key={item.role}>
            <div className="h-full rounded-xl border border-mist bg-surface p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-teal">
                {item.role}
              </p>
              <p className="mt-2 text-sm leading-6 text-muted">{item.line}</p>
            </div>
          </StaggerItem>
        ))}
      </Stagger>
    </section>
  );
}
