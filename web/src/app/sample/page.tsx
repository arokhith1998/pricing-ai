import { Suspense } from "react";
import Link from "next/link";
import { cookies } from "next/headers";
import { getDemo, type Diagnostic } from "@/lib/api";
import { money, pct } from "@/lib/format";
import { LEAD_COOKIE } from "@/lib/auth";
import Summary from "@/components/Summary";
import ApiError from "@/components/ApiError";
import LeadForm from "@/components/LeadForm";
import CountUp from "@/components/CountUp";

export const dynamic = "force-dynamic";

function MetricCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: React.ReactNode;
  sub?: string;
  accent?: "navy" | "coral";
}) {
  return (
    <div className="pk-fade-in rounded-xl border border-mist bg-surface p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="text-sm text-slate">{label}</div>
      <div
        className={`mt-1 text-3xl font-bold tabular-nums ${accent === "coral" ? "text-coral" : "text-fg"}`}
      >
        {value}
      </div>
      {sub ? <div className="mt-1 text-sm text-slate">{sub}</div> : null}
    </div>
  );
}

const STEPS: [string, string][] = [
  ["Your closed deals", "Won and lost"],
  ["Clean up", "Match accounts"],
  ["Measure", "Realization and win rate"],
  ["Diagnostic", "Where the money goes"],
  ["Predict", "Win probability"],
  ["Recommend", "The best discount"],
];

function Flow() {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {STEPS.map(([title, sub], i) => (
        <div key={title} className="flex items-center gap-2">
          <div className="rounded-lg border border-mist bg-surface px-3 py-2">
            <div className="text-sm font-semibold text-fg">{title}</div>
            <div className="text-xs text-slate">{sub}</div>
          </div>
          {i < STEPS.length - 1 ? <span className="text-slate">&rarr;</span> : null}
        </div>
      ))}
    </div>
  );
}

function LeadGate({ leak }: { leak: Diagnostic["leakage"] }) {
  return (
    <section className="rounded-xl border border-mist bg-surface p-6 shadow-sm">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h2 className="text-lg font-semibold text-fg">
            Unlock the full diagnostic
          </h2>
          <p className="mt-1 text-sm text-slate">
            That is {money(leak.excess_vs_reference_won)} of revenue discounted
            past the point that wins anything — pricing upside to pursue. The
            full read-out shows where it is and what to do:
          </p>
          <ul className="mt-3 space-y-1.5 text-sm text-ink">
            <li>• A written executive summary</li>
            <li>• Win rate vs discount, and the win point</li>
            <li>• Price realization by segment and governance gaps</li>
            <li>• Per-deal discount guidance with a plain &ldquo;why&rdquo;</li>
          </ul>
        </div>
        <div className="rounded-lg bg-surface-2 p-4">
          <LeadForm />
        </div>
      </div>
    </section>
  );
}

function FullSample() {
  return (
    <>
      <section className="rounded-xl border border-mist bg-surface p-5 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold text-fg">Executive summary</h2>
        <Suspense
          fallback={
            <p className="animate-pulse text-sm text-slate">Writing the summary&hellip;</p>
          }
        >
          <Summary />
        </Suspense>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Link
          href="/diagnostic"
          className="rounded-xl border border-mist bg-surface p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-teal hover:shadow-md"
        >
          <div className="text-lg font-semibold text-fg">Diagnostic →</div>
          <p className="mt-1 text-sm text-slate">
            Win rate vs discount, leakage lenses, quarter-end, governance, and the
            deals to look at first.
          </p>
        </Link>
        <Link
          href="/guidance"
          className="rounded-xl border border-mist bg-surface p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-teal hover:shadow-md"
        >
          <div className="text-lg font-semibold text-fg">Guidance →</div>
          <p className="mt-1 text-sm text-slate">
            Pick a deal and see the discount that maximizes expected value, with a
            plain-language why.
          </p>
        </Link>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold text-fg">How it works</h2>
        <Flow />
      </section>
    </>
  );
}

export default async function SamplePage() {
  const unlocked = Boolean((await cookies()).get(LEAD_COOKIE)?.value);

  let d: Diagnostic;
  try {
    d = await getDemo();
  } catch {
    return <ApiError />;
  }
  const o = d.overview;
  const l = d.leakage;

  return (
    <main className="mx-auto max-w-6xl space-y-8 px-6 py-8">
      <div>
        <p className="text-sm font-medium text-teal">Sample data</p>
        <h1 className="text-2xl font-bold text-fg">
          Where the money goes, and what to do about it
        </h1>
        <p className="mt-1 text-slate">
          A worked example on a realistic synthetic book of 2,000 closed deals.
        </p>
      </div>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Booked value (annual)"
          value={<CountUp to={o.booked_acv_won} format={money} />}
        />
        <MetricCard
          label="Price realization"
          value={<CountUp to={o.price_realization_won} format={pct} />}
          sub={`Average discount ${pct(o.avg_discount_won)}`}
        />
        <MetricCard
          label="Pricing upside to pursue"
          value={<CountUp to={l.excess_vs_reference_won} format={money} />}
          sub={`${pct(l.excess_pct_of_booked)} of booked value, discounted past the win point`}
          accent="coral"
        />
        <MetricCard
          label="Win rate"
          value={<CountUp to={o.win_rate} format={pct} />}
          sub={`${o.won.toLocaleString()} won, ${o.lost.toLocaleString()} lost`}
        />
      </section>

      {unlocked ? <FullSample /> : <LeadGate leak={l} />}
    </main>
  );
}
