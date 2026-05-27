"use client";

import { useState } from "react";
import type { Diagnostic } from "@/lib/api";
import { money, pct } from "@/lib/format";
import WinRateChart from "@/components/charts/WinRateChart";
import SegmentChart from "@/components/charts/SegmentChart";
import LeakageBars from "@/components/LeakageBars";

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
    <div className="rounded-xl border border-mist bg-white p-5 shadow-sm">
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

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-mist bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-navy">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Results({ d }: { d: Diagnostic }) {
  const { overview: o, leakage: l } = d;
  return (
    <div className="space-y-6">
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Booked value (annual)" value={money(o.booked_acv_won)} />
        <MetricCard
          label="Price realization"
          value={pct(o.price_realization_won)}
          sub={`Average discount ${pct(o.avg_discount_won)}`}
        />
        <MetricCard
          label="Pricing upside to pursue"
          value={money(l.excess_vs_reference_won)}
          sub={`${pct(l.excess_pct_of_booked)} of booked value, discounted past the win point`}
          accent="coral"
        />
        <MetricCard
          label="Win rate"
          value={pct(o.win_rate)}
          sub={`${o.won.toLocaleString()} won, ${o.lost.toLocaleString()} lost`}
        />
      </section>

      <Card title="Win rate vs discount">
        <WinRateChart bands={d.win_rate_by_band} reference={d.reference_discount} />
      </Card>

      {d.realization_by_segment?.length ? (
        <Card title="Price realization by segment">
          <SegmentChart rows={d.realization_by_segment} />
        </Card>
      ) : null}

      <Card title="Where the money goes">
        <LeakageBars leakage={l} />
      </Card>

      {d.top_leak_deals?.length ? (
        <Card title="Deals to look at first">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-mist text-left text-slate">
                  <th className="py-2 pr-4 font-medium">Account</th>
                  <th className="py-2 pr-4 font-medium">Segment</th>
                  <th className="py-2 pr-4 text-right font-medium">List value</th>
                  <th className="py-2 pr-4 text-right font-medium">Discount</th>
                  <th className="py-2 pr-4 text-right font-medium">Beyond win point</th>
                </tr>
              </thead>
              <tbody>
                {d.top_leak_deals.slice(0, 8).map((r) => (
                  <tr key={r.opportunity_id} className="border-b border-mist/60">
                    <td className="py-2 pr-4 font-medium text-navy">{r.resolved_account_name}</td>
                    <td className="py-2 pr-4 text-slate">{r.segment}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{money(r.list_acv)}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{pct(r.discount_pct)}</td>
                    <td className="py-2 pr-4 text-right font-semibold tabular-nums text-coral">
                      {money(r.excess_discount_dollars)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}
    </div>
  );
}

export default function UploadClient() {
  const [file, setFile] = useState<File | null>(null);
  const [res, setRes] = useState<Diagnostic | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    if (!file) return;
    setBusy(true);
    setError("");
    const fd = new FormData();
    fd.append("file", file);
    try {
      const r = await fetch("/api/diagnostic", { method: "POST", body: fd });
      if (!r.ok) {
        const b = await r.json().catch(() => ({}));
        throw new Error(b.error || "Analysis failed.");
      }
      setRes(await r.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-mist bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setRes(null);
            }}
            className="text-sm text-slate file:mr-3 file:rounded-lg file:border-0 file:bg-mist file:px-4 file:py-2 file:text-sm file:font-medium file:text-navy"
          />
          <button
            onClick={run}
            disabled={!file || busy}
            className="rounded-lg bg-navy px-5 py-2.5 font-medium text-white transition hover:bg-navy/90 disabled:opacity-50"
          >
            {busy ? "Analyzing…" : "Run the diagnostic"}
          </button>
        </div>
        {error ? <p className="mt-3 text-sm text-coral">{error}</p> : null}
        <p className="mt-3 text-xs text-slate">
          Your file is processed to produce the analysis and is not stored.
        </p>
      </section>

      {res ? <Results d={res} /> : null}
    </div>
  );
}
