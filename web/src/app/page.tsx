import { Suspense } from "react";
import { getDemo, type Diagnostic } from "@/lib/api";
import Summary from "@/components/Summary";

// Rendered per request (it reads live data from the API), not at build time.
export const dynamic = "force-dynamic";

const money = (x: number) => `$${Math.round(x).toLocaleString()}`;
const pct = (x: number) => `${(x * 100).toFixed(1)}%`;

function KeelMark() {
  return (
    <svg width="32" height="32" viewBox="0 0 48 48" aria-hidden>
      <line x1="9" y1="19" x2="39" y2="19" stroke="#0c2d48" strokeWidth="3" strokeLinecap="round" />
      <path d="M13 19 Q24 43 35 19" fill="none" stroke="#17b8a6" strokeWidth="4" strokeLinecap="round" />
    </svg>
  );
}

function Header() {
  return (
    <header className="border-b border-mist bg-white">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-6 py-4">
        <KeelMark />
        <div>
          <div className="text-xl font-extrabold tracking-tight">
            <span className="text-navy">Price</span>
            <span className="text-teal">keel</span>
          </div>
          <div className="-mt-1 text-xs text-slate">
            Keep your pricing on an even keel.
          </div>
        </div>
      </div>
    </header>
  );
}

function MetricCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: "navy" | "coral";
}) {
  return (
    <div className="pk-fade-in rounded-xl border border-mist bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="text-sm text-slate">{label}</div>
      <div
        className={`mt-1 text-3xl font-bold tabular-nums ${accent === "coral" ? "text-coral" : "text-navy"}`}
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
          <div className="rounded-lg border border-mist bg-white px-3 py-2">
            <div className="text-sm font-semibold text-navy">{title}</div>
            <div className="text-xs text-slate">{sub}</div>
          </div>
          {i < STEPS.length - 1 ? <span className="text-slate">&rarr;</span> : null}
        </div>
      ))}
    </div>
  );
}

function ApiDown() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-6xl px-6 py-16">
        <h1 className="text-2xl font-bold text-navy">Start the API</h1>
        <p className="mt-2 text-slate">
          The dashboard could not reach the Pricekeel API. Start it with:
        </p>
        <pre className="mt-3 rounded-lg bg-navy p-4 text-sm text-white">
          uvicorn api.main:app --port 8000
        </pre>
      </main>
    </div>
  );
}

export default async function Page() {
  let d: Diagnostic;
  try {
    d = await getDemo();
  } catch {
    return <ApiDown />;
  }
  const o = d.overview;
  const l = d.leakage;

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-6xl space-y-8 px-6 py-8">
        <h1 className="text-2xl font-bold text-navy">
          Where the money goes, and what to do about it
        </h1>

        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="Booked value (annual)" value={money(o.booked_acv_won)} />
          <MetricCard
            label="Price realization"
            value={pct(o.price_realization_won)}
            sub={`Average discount ${pct(o.avg_discount_won)}`}
          />
          <MetricCard
            label="Money beyond the win point"
            value={money(l.excess_vs_reference_won)}
            sub={`${pct(l.excess_pct_of_booked)} of booked value`}
            accent="coral"
          />
          <MetricCard
            label="Win rate"
            value={pct(o.win_rate)}
            sub={`${o.won.toLocaleString()} won, ${o.lost.toLocaleString()} lost`}
          />
        </section>

        <section className="rounded-xl border border-mist bg-white p-5 shadow-sm">
          <p className="text-ink">
            <span className="font-semibold">The short version. </span>
            Win rate stops improving past about a {pct(l.reference_threshold)}{" "}
            discount, yet {money(l.excess_vs_reference_won)} (
            {pct(l.excess_pct_of_booked)} of booked value) was discounted beyond
            that. This is a list to investigate, not a refund.
          </p>
        </section>

        <section className="rounded-xl border border-mist bg-white p-5 shadow-sm">
          <h2 className="mb-2 text-lg font-semibold text-navy">
            Executive summary
          </h2>
          <Suspense
            fallback={
              <p className="animate-pulse text-sm text-slate">
                Writing the summary&hellip;
              </p>
            }
          >
            <Summary />
          </Suspense>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-navy">How it works</h2>
          <Flow />
        </section>
      </main>
    </div>
  );
}
