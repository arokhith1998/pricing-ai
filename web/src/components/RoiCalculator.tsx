"use client";

import { useMemo, useState } from "react";
import { money, pct } from "@/lib/format";

// Rough on-page estimator. Calibrated from the sample:
//   ARR proxy = booked_acv_won ($67M), avg_discount ~14%, reference 5%,
//   excess$ ~ $11.2M ≈ 16.7% of booked.
// We approximate: upside ≈ booked * (avg_discount − 5%) * 0.6
// The 0.6 reflects that some "excess" was actually needed to win
// (we are correlational, not causal — kept honest).

const ARR_BUCKETS: { label: string; mid: number }[] = [
  { label: "$10M", mid: 10_000_000 },
  { label: "$30M", mid: 30_000_000 },
  { label: "$60M", mid: 60_000_000 },
  { label: "$120M", mid: 120_000_000 },
  { label: "$300M", mid: 300_000_000 },
];

const REFERENCE = 0.05;
const ATTRIB = 0.6;

export default function RoiCalculator() {
  const [arr, setArr] = useState(60_000_000);
  const [discount, setDiscount] = useState(0.14);

  const upside = useMemo(() => {
    const excess = Math.max(0, discount - REFERENCE);
    return arr * excess * ATTRIB;
  }, [arr, discount]);

  const pctOfArr = arr > 0 ? upside / arr : 0;

  return (
    <div className="rounded-2xl border border-teal/30 bg-surface p-6 pk-upside-glow">
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 md:items-center">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-teal">
            Back-of-envelope estimator
          </p>
          <h3 className="mt-1 text-xl font-bold text-fg">
            What might your pricing upside look like?
          </h3>
          <p className="mt-1 text-sm text-muted">
            Move the sliders. The math is the same logic our diagnostic uses,
            applied to round numbers. Your real number comes from your CSV.
          </p>

          <div className="mt-5 space-y-4">
            <div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted">Booked ACV (annual)</span>
                <span className="font-semibold text-fg tabular-nums">{money(arr)}</span>
              </div>
              <input
                type="range"
                min={0}
                max={ARR_BUCKETS.length - 1}
                value={ARR_BUCKETS.findIndex((b) => b.mid === arr)}
                onChange={(e) => setArr(ARR_BUCKETS[+e.target.value].mid)}
                className="mt-1 w-full accent-teal"
              />
              <div className="flex justify-between text-[10px] text-muted">
                {ARR_BUCKETS.map((b) => (
                  <span key={b.label}>{b.label}</span>
                ))}
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted">Average discount given</span>
                <span className="font-semibold text-fg tabular-nums">{pct(discount)}</span>
              </div>
              <input
                type="range"
                min={0}
                max={0.35}
                step={0.01}
                value={discount}
                onChange={(e) => setDiscount(+e.target.value)}
                className="mt-1 w-full accent-teal"
              />
              <div className="flex justify-between text-[10px] text-muted">
                <span>0%</span>
                <span>10%</span>
                <span>20%</span>
                <span>30%</span>
              </div>
            </div>
          </div>
        </div>

        <div className="text-center md:text-left">
          <div className="text-xs font-semibold uppercase tracking-wider text-coral">
            Estimated pricing upside (annual)
          </div>
          <div className="mt-2 text-5xl font-extrabold tabular-nums text-coral">
            {money(upside)}
          </div>
          <div className="mt-1 text-sm text-muted">
            ≈ {pct(pctOfArr)} of booked value, past the 5% reference. To pursue,
            not a refund — your real number plus the deal-level list comes from
            the diagnostic on your CSV.
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-center gap-3 md:justify-start">
            <a
              href="/sample"
              className="rounded-lg bg-teal px-4 py-2 text-sm font-semibold text-bg transition hover:scale-[1.03]"
            >
              See the sample
            </a>
            <a
              href="/upload"
              className="rounded-lg border border-mist bg-surface px-4 py-2 text-sm font-medium text-fg transition hover:border-teal"
            >
              Run it on your data
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
