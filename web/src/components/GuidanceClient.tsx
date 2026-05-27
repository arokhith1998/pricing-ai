"use client";

import { useEffect, useState } from "react";
import type { Deal, Recommendation } from "@/lib/api";
import { money, pct, pct0 } from "@/lib/format";
import ExpectedValueChart from "@/components/charts/ExpectedValueChart";

function Stat({
  label,
  value,
  accent,
  sub,
}: {
  label: string;
  value: string;
  accent?: "navy" | "teal" | "coral";
  sub?: string;
}) {
  const color =
    accent === "coral" ? "text-coral" : accent === "teal" ? "text-teal" : "text-fg";
  return (
    <div className="rounded-xl border border-mist bg-surface p-4">
      <div className="text-sm text-slate">{label}</div>
      <div className={`mt-1 text-2xl font-bold tabular-nums ${color}`}>{value}</div>
      {sub ? <div className="mt-0.5 text-xs text-slate">{sub}</div> : null}
    </div>
  );
}

function FactorRow({
  label,
  value,
  direction,
}: {
  label: string;
  value: string;
  direction: "up" | "down";
}) {
  const up = direction === "up";
  return (
    <li className="flex items-center justify-between gap-3 border-b border-mist/60 py-2 last:border-0">
      <span className="text-sm text-ink">
        <span className="font-medium">{label}</span>
        <span className="text-slate"> · {value}</span>
      </span>
      <span
        className={`flex items-center gap-1 text-xs font-medium ${
          up ? "text-green" : "text-coral"
        }`}
      >
        {up ? "▲ raises win chance" : "▼ lowers win chance"}
      </span>
    </li>
  );
}

export default function GuidanceClient({ deals }: { deals: Deal[] }) {
  const [selected, setSelected] = useState(deals[0]?.opportunity_id ?? "");
  const [rec, setRec] = useState<Recommendation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    setLoading(true);
    setError(false);
    fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ opportunity_id: selected }),
    })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((data: Recommendation) => {
        if (!cancelled) setRec(data);
      })
      .catch(() => !cancelled && setError(true))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [selected]);

  const lower = rec ? rec.recommended_discount < rec.current_discount : false;

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-mist bg-surface p-5 shadow-sm">
        <label htmlFor="deal" className="text-sm font-medium text-slate">
          Pick a deal
        </label>
        <select
          id="deal"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          className="mt-2 w-full rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm text-ink focus:border-teal focus:outline-none"
        >
          {deals.map((d) => (
            <option key={d.opportunity_id} value={d.opportunity_id}>
              {d.resolved_account_name} · {d.segment} · list {money(d.list_acv)}
            </option>
          ))}
        </select>
      </div>

      {loading && !rec ? (
        <p className="animate-pulse text-sm text-slate">Working out the best discount…</p>
      ) : null}

      {error ? (
        <p className="text-sm text-coral">
          Could not load guidance for this deal. Is the API running?
        </p>
      ) : null}

      {rec ? (
        <div className={`space-y-6 ${loading ? "opacity-60" : ""}`}>
          <div className="rounded-xl border border-mist bg-surface p-5 shadow-sm">
            <p className="text-lg text-ink">
              On <span className="font-semibold text-fg">{rec.account}</span>, the
              model suggests{" "}
              {lower ? "lowering the discount to " : "a discount of "}
              <span className="font-semibold text-teal">
                {pct0(rec.recommended_discount)}
              </span>{" "}
              {lower ? (
                <>
                  from {pct0(rec.current_discount)}. That gives up less price while
                  barely moving the odds of winning, for about{" "}
                  <span className="font-semibold text-fg">{money(rec.uplift)}</span>{" "}
                  more in expected value.
                </>
              ) : (
                <>to maximize expected value on a {money(rec.list_acv)} list deal.</>
              )}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Current discount" value={pct0(rec.current_discount)} />
            <Stat
              label="Recommended discount"
              value={pct0(rec.recommended_discount)}
              accent="teal"
            />
            <Stat
              label="Win probability"
              value={pct0(rec.win_prob_at_rec)}
              sub={`was ${pct0(rec.win_prob_at_current)} at the current discount`}
            />
            <Stat
              label="Expected value gain"
              value={money(rec.uplift)}
              accent={rec.uplift >= 0 ? "navy" : "coral"}
              sub="vs the discount given"
            />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
            <div className="rounded-xl border border-mist bg-surface p-5 shadow-sm lg:col-span-3">
              <h2 className="text-lg font-semibold text-fg">
                Expected value vs discount
              </h2>
              <p className="mt-1 text-sm text-slate">
                Expected value peaks where extra win probability stops covering the
                price you give away. Win probability is the dashed line.
              </p>
              <div className="mt-4">
                <ExpectedValueChart
                  curve={rec.curve}
                  current={rec.current_discount}
                  recommended={rec.recommended_discount}
                />
              </div>
            </div>

            <div className="rounded-xl border border-mist bg-surface p-5 shadow-sm lg:col-span-2">
              <h2 className="text-lg font-semibold text-fg">
                Why, for this deal
              </h2>
              <p className="mt-1 text-sm text-slate">
                The factors that move this deal&apos;s win chance the most.
              </p>
              <ul className="mt-3">
                {rec.top_factors.map((f) => (
                  <FactorRow
                    key={f.label}
                    label={f.label}
                    value={f.value}
                    direction={f.direction}
                  />
                ))}
              </ul>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
