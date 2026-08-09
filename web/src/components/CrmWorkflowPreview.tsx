import Link from "next/link";

const CONTEXT = [
  ["Account", "Northstar Cloud"],
  ["Product", "Data Platform · Enterprise"],
  ["Requested discount", "23%"],
  ["Contract", "$420K ACV · 12 months"],
];

const STEPS = [
  {
    number: "01",
    title: "Read the live opportunity",
    body:
      "Pricekeel maps Salesforce Opportunity, Account, product, price, and outcome fields without asking reps to re-enter the deal.",
  },
  {
    number: "02",
    title: "Price the exception",
    body:
      "The requested discount is compared with the closest historical wins and losses, the segment win curve, and policy. Cited public competitor context is shown alongside it as advisory information.",
  },
  {
    number: "03",
    title: "Decide and write back",
    body:
      "Deal Desk accepts the recommendation or requests an override with a reason. The recommendation, evidence, actor, and reason stay together in an audit trail and can write back to Salesforce.",
  },
];

export default function CrmWorkflowPreview() {
  return (
    <section id="workflow" aria-label="Salesforce pricing workflow" className="scroll-mt-24">
      <div className="text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal">
          Before approval, not after quarter close
        </p>
        <h2 className="mt-2 text-2xl font-bold text-fg sm:text-3xl">
          One pricing decision, from Opportunity to audit trail
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-muted sm:text-base">
          Pricekeel participates in the workflow your team already runs. It
          turns CRM history into a recommendation while the deal is still
          changeable, then records what the team decided and why.
        </p>
        <p className="mx-auto mt-2 max-w-2xl text-xs leading-5 text-muted">
          V1 governs the discount on committed and annualized ACV.
          Commitment-tier and overage-rate awareness are on the roadmap.
        </p>
      </div>

      <div className="pk-card mx-auto mt-8 overflow-hidden rounded-2xl border border-mist shadow-2xl shadow-black/20">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-mist bg-surface px-4 py-3 sm:px-5">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-teal/10 text-teal">
              <svg aria-hidden width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
              </svg>
            </span>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                Salesforce opportunity
              </p>
              <p className="text-sm font-semibold text-fg">Northstar Cloud · Expansion</p>
            </div>
          </div>
          <span className="rounded-full border border-amber/40 bg-amber/10 px-2.5 py-1 text-xs font-semibold text-amber">
            Discount exception pending
          </span>
        </div>

        <div className="grid bg-surface lg:grid-cols-[0.8fr_1.35fr_0.95fr]">
          <div className="border-b border-mist p-5 lg:border-b-0 lg:border-r">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">
              Deal context
            </p>
            <dl className="mt-4 space-y-3">
              {CONTEXT.map(([label, value]) => (
                <div key={label} className="flex items-start justify-between gap-4 border-b border-mist/70 pb-2 last:border-0">
                  <dt className="text-xs text-muted">{label}</dt>
                  <dd className={`text-right text-xs font-medium ${label === "Requested discount" ? "text-coral" : "text-fg"}`}>
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
            <div className="mt-5 rounded-lg border border-mist bg-surface-2 p-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-teal">
                External context
              </p>
              <p className="mt-1 text-xs leading-5 text-muted">
                Two competitor pricing changes and one investor-call signal,
                each linked to its public source.
              </p>
            </div>
          </div>

          <div className="border-b border-mist p-5 lg:border-b-0 lg:border-r">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-teal">
                  Pricekeel recommendation
                </p>
                <h3 className="mt-1 text-xl font-bold text-fg">Hold at 16%</h3>
              </div>
              <span className="rounded-md border border-teal/40 bg-teal/10 px-2 py-1 text-xs font-semibold text-teal">
                Illustrative deal
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-muted">
              In the closest Enterprise expansion cohort, discounts above 17%
              did not improve win rate enough to offset the price given away.
            </p>

            <div className="mt-5 grid grid-cols-3 gap-2">
              {[
                ["Requested", "23%", "text-coral"],
                ["Guardrail", "14–17%", "text-teal"],
                ["Price retained", "$29.4K", "text-fg"],
              ].map(([label, value, color]) => (
                <div key={label} className="rounded-lg border border-mist bg-surface-2 p-3">
                  <div className="text-xs font-semibold uppercase tracking-wider text-muted">{label}</div>
                  <div className={`mt-1 text-sm font-bold tabular-nums sm:text-lg ${color}`}>{value}</div>
                </div>
              ))}
            </div>

            <div className="mt-4 rounded-lg border border-mist bg-surface-2 p-3">
              <div className="flex items-center justify-between gap-2 text-xs font-semibold uppercase tracking-wider text-muted">
                <span>Evidence used</span>
                <span>47 comparable deals</span>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-mist">
                <div className="h-full w-[68%] rounded-full bg-teal" />
              </div>
              <p className="mt-2 text-xs leading-5 text-muted">
                Segment history · deal size · policy
              </p>
            </div>
            <div className="mt-2 rounded-lg border border-mist/70 bg-surface-2/60 p-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-amber">
                Advisory context, does not move the guardrail
              </p>
              <p className="mt-1 text-xs leading-5 text-muted">
                Public competitor sources
              </p>
            </div>
          </div>

          <div className="p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">
              Decision controls
            </p>
            <div className="mt-4 space-y-2">
              <button type="button" className="w-full rounded-lg bg-teal px-3 py-2.5 text-left text-xs font-semibold text-bg">
                Accept 16% recommendation
              </button>
              <button type="button" className="w-full rounded-lg border border-mist bg-surface-2 px-3 py-2.5 text-left text-xs font-semibold text-fg">
                Request override with a reason
              </button>
            </div>
            <div className="mt-5 border-t border-mist pt-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">On decision</p>
              <ul className="mt-2 space-y-2 text-xs text-muted">
                <li className="flex gap-2"><span className="text-teal">✓</span> Append audit event</li>
                <li className="flex gap-2"><span className="text-teal">✓</span> Capture evidence snapshot</li>
                <li className="flex gap-2"><span className="text-teal">✓</span> Optional Salesforce writeback</li>
              </ul>
              <p className="mt-3 text-xs leading-5 text-muted">
                Least-privilege read of Opportunity data. Writeback creates a
                Salesforce Task only, never an edit to Opportunity fields.
                OAuth tokens are encrypted and revocable.
              </p>
            </div>
          </div>
        </div>
      </div>

      <ol className="mt-6 grid gap-3 md:grid-cols-3">
        {STEPS.map((step) => (
          <li key={step.number} className="rounded-xl border border-mist bg-surface p-4">
            <div className="flex items-baseline gap-2">
              <span className="text-xs font-bold text-teal">{step.number}</span>
              <h3 className="text-sm font-semibold text-fg">{step.title}</h3>
            </div>
            <p className="mt-2 text-xs leading-5 text-muted">{step.body}</p>
          </li>
        ))}
      </ol>

      <div className="mt-5 text-center">
        <Link href="/contact" className="text-sm font-semibold text-teal hover:underline">
          Walk through one discount exception →
        </Link>
      </div>
    </section>
  );
}
