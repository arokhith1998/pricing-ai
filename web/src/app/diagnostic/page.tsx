import { getDemo, type Diagnostic } from "@/lib/api";
import { money, pct } from "@/lib/format";
import Reveal from "@/components/Reveal";
import ApiError from "@/components/ApiError";
import WinRateChart from "@/components/charts/WinRateChart";
import SegmentChart from "@/components/charts/SegmentChart";
import LeakageBars from "@/components/LeakageBars";

// Reads live data from the API on every request.
export const dynamic = "force-dynamic";

function Card({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-mist bg-surface p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-fg">{title}</h2>
      {subtitle ? <p className="mt-1 text-sm text-slate">{subtitle}</p> : null}
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Flag({ on, label }: { on: boolean; label: string }) {
  if (!on) return <span className="text-mist">—</span>;
  return (
    <span className="rounded-full bg-coral/10 px-2 py-0.5 text-xs font-medium text-coral">
      {label}
    </span>
  );
}

export default async function DiagnosticPage() {
  let d: Diagnostic;
  try {
    d = await getDemo();
  } catch {
    return <ApiError />;
  }

  const { leakage: l, quarter_end: qe, governance: g } = d;

  return (
    <main className="mx-auto max-w-6xl space-y-8 px-6 py-8">
      <Reveal>
        <h1 className="text-2xl font-bold text-fg">Diagnostic</h1>
        <p className="mt-1 max-w-2xl text-slate">
          Where discount turns into wins, and where it just gives money away.
          Everything here is measured from your closed deals.
        </p>
      </Reveal>

      <Reveal delay={0.05}>
        <Card
          title="Win rate vs discount"
          subtitle={`Win rate climbs with discount, then flattens. Past the win point (about ${pct(
            l.reference_threshold,
            0,
          )}), extra discount buys almost no extra wins. The shaded band is the range we are confident about.`}
        >
          <WinRateChart bands={d.win_rate_by_band} reference={d.reference_discount} />
        </Card>
      </Reveal>

      <Reveal delay={0.05}>
        <Card
          title="Price realization by segment"
          subtitle="Share of list value you actually keep, by segment. The lowest bar is where price erodes most."
        >
          <SegmentChart rows={d.realization_by_segment} />
        </Card>
      </Reveal>

      {Object.entries(d.hierarchy_slices).map(([dim, rows]) => {
        const labels: Record<string, string> = {
          business_unit: "business unit",
          product_line: "product line",
          product_family: "product family",
          sku: "SKU",
        };
        const label = labels[dim] ?? dim;
        return (
          <Reveal key={dim} delay={0.05}>
            <Card
              title={`Price realization by ${label}`}
              subtitle={`Same lens, sliced by ${label}. The lowest bar is where price erodes most.`}
            >
              <SegmentChart rows={rows} dimKey={dim} />
            </Card>
          </Reveal>
        );
      })}

      <Reveal delay={0.05}>
        <Card
          title="Where the money goes"
          subtitle="Three views of the same discounting, from a plain description to the strongest claim worth acting on."
        >
          <LeakageBars leakage={l} />
        </Card>
      </Reveal>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {qe ? (
          <Reveal delay={0.05}>
            <Card title="Quarter-end effect">
              <p className="text-ink">
                Deals closing near quarter end are discounted{" "}
                <span className="font-semibold text-coral">
                  {pct(qe.lift)} more
                </span>{" "}
                on average ({pct(qe.qe_avg_discount)} vs {pct(qe.rest_avg_discount)}).
              </p>
              <p className="mt-2 text-sm text-slate">
                That timing pattern accounts for about{" "}
                {money(qe.attributable_discount_won)} of discount on won deals.
              </p>
            </Card>
          </Reveal>
        ) : null}

        <Reveal delay={0.05}>
          <Card title="Governance gaps">
            <p className="text-ink">
              <span className="font-semibold">
                {g.off_policy_unapproved_won.toLocaleString()}
              </span>{" "}
              won deals were discounted above policy with{" "}
              <span className="font-semibold">no recorded approver</span>.
            </p>
            <p className="mt-2 text-sm text-slate">
              That is {money(g.unapproved_discount_dollars)} discounted without a
              sign-off, out of {g.off_policy_won.toLocaleString()} off-policy wins.
            </p>
          </Card>
        </Reveal>
      </div>

      <Reveal delay={0.05}>
        <Card
          title="Deals to look at first"
          subtitle="Ranked by discount given beyond the win point. A prioritized list to investigate, not a refund figure."
        >
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-mist text-left text-slate">
                  <th className="py-2 pr-4 font-medium">Account</th>
                  <th className="py-2 pr-4 font-medium">Segment</th>
                  <th className="py-2 pr-4 text-right font-medium">List value</th>
                  <th className="py-2 pr-4 text-right font-medium">Discount</th>
                  <th className="py-2 pr-4 text-right font-medium">Beyond win point</th>
                  <th className="py-2 pr-4 font-medium">Flags</th>
                </tr>
              </thead>
              <tbody>
                {d.top_leak_deals.slice(0, 8).map((row) => (
                  <tr key={row.opportunity_id} className="border-b border-mist/60">
                    <td className="py-2 pr-4 font-medium text-fg">
                      {row.resolved_account_name}
                    </td>
                    <td className="py-2 pr-4 text-slate">{row.segment}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">
                      {money(row.list_acv)}
                    </td>
                    <td className="py-2 pr-4 text-right tabular-nums">
                      {pct(row.discount_pct)}
                    </td>
                    <td className="py-2 pr-4 text-right font-semibold tabular-nums text-coral">
                      {money(row.excess_discount_dollars)}
                    </td>
                    <td className="py-2 pr-4">
                      <span className="flex flex-wrap gap-1">
                        <Flag on={row.competitor_present} label="Competitor" />
                        <Flag on={row.is_quarter_end} label="Quarter end" />
                        <Flag on={row.off_policy_unapproved} label="No approval" />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </Reveal>
    </main>
  );
}
