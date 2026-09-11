"use client";

import { useEffect, useState } from "react";
import type { Deal, Recommendation, ComparableDeal, BandContext, Confidence } from "@/lib/api";
import { money, moneyShort, pct, pct0 } from "@/lib/format";
import ExpectedValueChart from "@/components/charts/ExpectedValueChart";
import DecisionControl from "@/components/DecisionControl";

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

function OutcomeChip({ won }: { won: boolean }) {
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-xs font-medium ${
        won ? "border-green/40 text-green" : "border-coral/40 text-coral"
      }`}
    >
      {won ? "won" : "lost"}
    </span>
  );
}

function Comparables({ rows }: { rows: ComparableDeal[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-fg">Deals like this one</h3>
      <p className="mt-0.5 text-xs text-slate">
        The closest closed deals by segment, size, and discount, won and lost.
      </p>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-mist text-left text-slate">
              <th className="py-1.5 pr-3 font-medium">Account</th>
              <th className="py-1.5 pr-3 text-right font-medium">List</th>
              <th className="py-1.5 pr-3 text-right font-medium">Discount</th>
              <th className="py-1.5 font-medium">Outcome</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.opportunity_id} className="border-b border-mist/60">
                <td className="py-1.5 pr-3">
                  <span className="font-medium text-fg">{r.resolved_account_name}</span>
                  <span className="text-xs text-slate"> · {r.industry ?? r.segment}</span>
                </td>
                <td className="py-1.5 pr-3 text-right tabular-nums text-ink">{moneyShort(r.list_acv)}</td>
                <td className="py-1.5 pr-3 text-right tabular-nums text-ink">{pct0(r.discount_pct)}</td>
                <td className="py-1.5"><OutcomeChip won={r.is_won} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function BandCohort({ ctx }: { ctx: BandContext }) {
  const maxWin = Math.max(...ctx.bands.map((b) => b.win_rate), 0.0001);
  return (
    <div>
      <h3 className="text-sm font-semibold text-fg">
        Win rate by discount band · {ctx.segment}
      </h3>
      <p className="mt-0.5 text-xs text-slate">
        How win rate varied by discount across{" "}
        {ctx.cohort_deals.toLocaleString()} {ctx.segment} deals. The
        recommendation rides this observed curve, not a single global rule.
      </p>
      <ul className="mt-3 space-y-1.5">
        {ctx.bands.map((b) => {
          const isCurrent = b.band === ctx.current_band;
          const isRec = b.band === ctx.recommended_band;
          return (
            <li key={b.band} className="flex items-center gap-2 text-xs">
              <span className="w-14 shrink-0 tabular-nums text-slate">{b.band}</span>
              <span className="relative h-3 flex-1 overflow-hidden rounded bg-mist/50">
                <span
                  className={`absolute inset-y-0 left-0 rounded ${
                    isRec ? "bg-teal" : isCurrent ? "bg-amber" : "bg-slate/40"
                  }`}
                  style={{ width: `${(b.win_rate / maxWin) * 100}%` }}
                />
              </span>
              <span className="w-10 shrink-0 text-right tabular-nums text-ink">
                {pct(b.win_rate, 0)}
              </span>
              <span className="w-20 shrink-0 text-right">
                {isRec ? (
                  <span className="font-medium text-teal">recommended</span>
                ) : isCurrent ? (
                  <span className="font-medium text-amber">current</span>
                ) : (
                  <span className="text-slate">{b.deals.toLocaleString()} deals</span>
                )}
              </span>
            </li>
          );
        })}
      </ul>
      {!ctx.bands.some((b) => b.band === ctx.recommended_band) ? (
        <p className="mt-2 text-xs text-slate">
          <span className="font-medium text-teal">
            Recommended band {ctx.recommended_band}.
          </span>{" "}
          No {ctx.segment}{" "}deals sit this low, so there is no bar to show:
          the model is pointing below this segment&apos;s historical discount
          floor, which is itself the signal.
        </p>
      ) : null}
    </div>
  );
}

// Below this many percentage points of change in win probability, the
// headline sentence calls the move "barely" moving the odds. Chosen as a
// materiality cut, not a statistical one: the confidence caveat below the
// headline already tells the reader this model calibrates within a few
// points of the actual win rate, so a 1-2 point shift reads as noise a
// reasonable rep would not act on. Above the threshold the sentence must
// name the actual change instead of describing it as negligible, since
// that is exactly the deal where the tradeoff being made is real.
export const WIN_PROB_BARELY_THRESHOLD_PTS = 2;

function ConfidenceCaveat({ c }: { c: Confidence }) {
  return (
    <div className="mt-5 rounded-lg border border-mist bg-surface-2 p-4 text-xs leading-relaxed text-slate">
      <span className="font-semibold text-ink">How to read this.</span> These
      patterns are correlational, not causal: bigger or more competitive deals
      attract bigger discounts, so some of the gap is justified. Treat the
      recommendation as decision support for a human, not an instruction. On
      held-out deals the model ranks at {c.auc.toFixed(2)} AUC and calibrates to{" "}
      {pct(c.mean_pred, 0)} predicted versus {pct(c.base_rate, 0)} actual win
      rate, learned from {c.n_train.toLocaleString()} of your closed deals.
    </div>
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
    // Synchronizing UI state with the fetch about to start. The new
    // react-hooks/set-state-in-effect rule (React 19) fires on the first
    // setState; the cancellation flag below is the unmount-safety the rule
    // worries about. Both setStates share the same justification, but the
    // linter only flags the first — the eslint-disable for setError(false)
    // would itself become "unused directive" and re-trigger lint.
    // eslint-disable-next-line react-hooks/set-state-in-effect
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
  // Percentage-point change in win probability, derived from the same
  // rounded integers the stat tile below renders (pct0 of each probability),
  // not from rounding the raw difference. Rounding the raw difference and
  // rounding each tile value independently can disagree by a point, which is
  // exactly the contradiction this component exists to prevent.
  const recPts = rec ? Math.round(rec.win_prob_at_rec * 100) : 0;
  const curPts = rec ? Math.round(rec.win_prob_at_current * 100) : 0;
  const dWinPts = rec ? recPts - curPts : 0;

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
                  from {pct0(rec.current_discount)}
                  {!Number.isFinite(dWinPts) ? (
                    <>
                      . That changes the discount, for about{" "}
                    </>
                  ) : Math.abs(dWinPts) <= WIN_PROB_BARELY_THRESHOLD_PTS ? (
                    <>
                      . That gives up less price while barely moving the odds
                      of winning, for about{" "}
                    </>
                  ) : dWinPts < 0 ? (
                    <>
                      , for a {Math.abs(dWinPts)} point drop in
                      win probability, worth about{" "}
                    </>
                  ) : (
                    <>
                      , which also lifts the odds of winning by{" "}
                      {dWinPts} points, for about{" "}
                    </>
                  )}
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

          {/* The evidence behind the recommendation — comparable deals, the
              win-rate curve segment it came from, and the confidence caveat.
              One screen, defensible in a pricing committee. */}
          <section className="rounded-xl border border-mist bg-surface p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-fg">The evidence behind this</h2>
            <p className="mt-1 text-sm text-slate">
              Similar deals, the win-rate curve segment this recommendation came
              from, and what the model can and cannot claim.
            </p>
            <div className="mt-4 grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Comparables rows={rec.comparables} />
              <BandCohort ctx={rec.band_context} />
            </div>
            <ConfidenceCaveat c={rec.confidence} />
          </section>

          {/* The governance loop closes here: the recommendation above, the
              decision below. Keyed by deal so the control resets when the
              dropdown switches deals. */}
          <DecisionControl
            key={rec.opportunity_id}
            dealId={rec.opportunity_id}
            account={rec.account}
            recommendedDiscount={rec.recommended_discount}
          />
        </div>
      ) : null}
    </div>
  );
}
