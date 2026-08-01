"use client";

import { useMemo, useState } from "react";
import { money, moneyShort, pct } from "@/lib/format";
import { computeLeakage, POLICY_THRESHOLD } from "@/lib/leakage";

// Public, no-signup leakage estimator. The math is a faithful mirror of
// pricing/metrics.py (see web/src/lib/leakage.ts): we show the gross discount
// given back (a hard fact) and the slice above the 15% deal-desk line (an
// honest aggregate approximation), and we explicitly DO NOT invent the
// excess-vs-reference number that needs the real per-deal CSV. That refusal is
// the point: it is what makes the figure defensible in a pricing committee.

const ARR_PRESETS = [10_000_000, 30_000_000, 60_000_000, 120_000_000];

function Field({
  label, hint, children,
}: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-medium text-fg">{label}</span>
        {hint ? <span className="text-[11px] text-muted">{hint}</span> : null}
      </div>
      <div className="mt-1.5">{children}</div>
    </label>
  );
}

const inputCls =
  "w-full rounded-lg border border-mist bg-surface px-3 py-2 text-sm text-fg tabular-nums focus:border-teal focus:outline-none";

export default function LeakageCalculator() {
  const [arr, setArr] = useState(60_000_000);
  const [discountPct, setDiscountPct] = useState(18); // percent, as typed
  const [deals, setDeals] = useState<number | "">("");

  const r = useMemo(
    () =>
      computeLeakage({
        bookedAcv: arr,
        avgDiscount: discountPct / 100,
        deals: typeof deals === "number" ? deals : undefined,
      }),
    [arr, discountPct, deals],
  );

  return (
    <div className="rounded-2xl border border-teal/30 bg-surface p-6 pk-upside-glow">
      <p className="text-xs font-semibold uppercase tracking-wider text-teal">
        No signup. The math is shown.
      </p>
      <h3 className="mt-1 text-xl font-bold text-fg">
        How much discount are you giving back a year?
      </h3>

      <div className="mt-5 grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Inputs ---------------------------------------------------------- */}
        <div className="space-y-4">
          <Field label="Booked ACV / year" hint="post-discount, your ARR proxy">
            <input
              type="text"
              inputMode="numeric"
              value={arr ? arr.toLocaleString() : ""}
              onChange={(e) => {
                const n = Number(e.target.value.replace(/[^0-9]/g, ""));
                setArr(Number.isFinite(n) ? n : 0);
              }}
              className={inputCls}
            />
            <div className="mt-2 flex flex-wrap gap-1.5">
              {ARR_PRESETS.map((v) => (
                <button
                  key={v}
                  type="button"
                  onClick={() => setArr(v)}
                  className={`rounded-full border px-2.5 py-0.5 text-xs font-medium transition ${
                    arr === v
                      ? "border-teal bg-teal/10 text-teal"
                      : "border-mist text-muted hover:border-teal"
                  }`}
                >
                  {moneyShort(v)}
                </button>
              ))}
            </div>
          </Field>

          <Field label="Average discount" hint="list to booked, %">
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={0}
                max={40}
                step={1}
                value={discountPct}
                onChange={(e) => setDiscountPct(+e.target.value)}
                className="w-full accent-teal"
              />
              <div className="flex items-center gap-1">
                <input
                  type="text"
                  inputMode="decimal"
                  value={discountPct}
                  onChange={(e) => {
                    const n = Number(e.target.value.replace(/[^0-9.]/g, ""));
                    setDiscountPct(Number.isFinite(n) ? Math.min(95, n) : 0);
                  }}
                  className="w-14 rounded-lg border border-mist bg-surface px-2 py-1 text-sm text-fg tabular-nums focus:border-teal focus:outline-none"
                />
                <span className="text-sm text-muted">%</span>
              </div>
            </div>
          </Field>

          <Field label="Closed-won deals / year" hint="optional, for per-deal context">
            <input
              type="text"
              inputMode="numeric"
              placeholder="e.g. 400"
              value={deals === "" ? "" : deals.toLocaleString()}
              onChange={(e) => {
                const raw = e.target.value.replace(/[^0-9]/g, "");
                setDeals(raw === "" ? "" : Number(raw));
              }}
              className={inputCls}
            />
          </Field>
        </div>

        {/* Results --------------------------------------------------------- */}
        <div className="rounded-xl border border-mist bg-surface-2 p-5">
          <div className="text-xs font-semibold uppercase tracking-wider text-coral">
            Discount given back / year
          </div>
          <div className="mt-1 text-4xl font-extrabold tabular-nums text-coral">
            {money(r.grossDiscount)}
          </div>
          <div className="mt-1 text-sm text-muted">
            list {money(r.listAcv)} − booked {money(r.bookedAcv)} ·{" "}
            {pct(r.priceRealization)} price realization
            {r.perDealGross != null ? (
              <> · {money(r.perDealGross)} / deal</>
            ) : null}
          </div>

          <div className="mt-4 border-t border-mist pt-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-fg">
              Worth a closer look
            </div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-bold tabular-nums text-fg">
                {money(r.abovePolicy)}
              </span>
              <span className="text-sm text-muted">
                above the {pct(r.policyThreshold, 0)} policy line
              </span>
            </div>
            <p className="mt-1 text-xs leading-relaxed text-muted">
              ={" "}
              {discountPct > POLICY_THRESHOLD * 100
                ? `(${discountPct}% − ${pct(POLICY_THRESHOLD, 0)}) × list`
                : `0, your average sits at or below the ${pct(POLICY_THRESHOLD, 0)} line`}
              . This is the deal-desk lens. It is correlational, not a refund:
              some of that discount was needed to win. The real diagnostic clips
              every deal against your own win-rate curve, so it usually finds{" "}
              <span className="text-fg">more</span> than a blended average shows.
            </p>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            <a
              href="/sample"
              className="rounded-lg bg-teal px-4 py-2 text-sm font-semibold text-bg transition hover:scale-[1.03]"
            >
              See the real diagnostic
            </a>
            <a
              href="/crm"
              className="rounded-lg border border-mist bg-surface px-4 py-2 text-sm font-medium text-fg transition hover:border-teal"
            >
              Connect Salesforce
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
