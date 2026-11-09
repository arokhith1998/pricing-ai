// The readout and the win-rate-by-band probe. Everything here is a lookup of
// engine output on the synthetic 2,000-deal book, not a forecast. Data arrives
// from the caller (page.tsx), which builds it in src/lib/landing-sample.ts from
// src/data/sample-fallback.json. The probe reads win_rate_by_band and
// reference_discount.band_win_rate_ci only and calls no API, so the landing
// route stays force-static.
"use client";

import { useId, useState } from "react";
import { Card, SyntheticTag } from "@/components/ui";
import { pct } from "@/lib/format";
import type { ProbeBand } from "@/lib/landing-sample";
import CountUp from "@/components/CountUp";

export type DiagnosticPreviewData = {
  opportunities: number;
  bookedAcvWon: number;
  priceRealizationWon: number;
  avgDiscountWon: number;
  winRate: number;
  bands: ProbeBand[];
  peakBand: string;
  initialBand: string;
};

function Kpi({ label, value, sub }: { label: string; value: React.ReactNode; sub: string }) {
  return (
    <div className="min-w-0">
      <p className="pk-small m-0 text-muted">{label}</p>
      <p className="pk-figure m-0 mt-1">{value}</p>
      <p className="pk-small m-0 mt-1 text-muted">{sub}</p>
    </div>
  );
}

export default function DiagnosticPreview({ data }: { data: DiagnosticPreviewData }) {
  const group = useId();
  const [selected, setSelected] = useState(data.initialBand);
  const band = data.bands.find((b) => b.label === selected) ?? data.bands[0];
  const peak = data.bands.find((b) => b.label === data.peakBand) ?? data.bands[0];
  const points = Math.round((peak.winRate - band.winRate) * 100);

  return (
    <div>
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        <Kpi
          label="Booked value"
          value={<CountUp to={data.bookedAcvWon} format="moneyShort" />}
          sub={`${data.opportunities.toLocaleString()} opportunities`}
        />
        <Kpi
          label="Price realization"
          value={<CountUp to={data.priceRealizationWon} format="pct" />}
          sub={`average discount ${pct(data.avgDiscountWon)}`}
        />
        <Kpi
          label="Win rate"
          value={<CountUp to={data.winRate} format="pct" />}
          sub="of all opportunities"
        />
      </div>
      <SyntheticTag className="mt-4" />

      <Card tone="inset" className="mt-6">
        <fieldset className="m-0 min-w-0 border-0 p-0">
          <legend className="pk-h3 m-0 p-0">Win rate by discount band</legend>
          <p className="pk-small m-0 mt-1 text-muted">
            Pick a band. This is a lookup of the synthetic book, not a forecast.
          </p>
          <div className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-6">
            {data.bands.map((b) => (
              <label
                key={b.label}
                className={`flex min-h-11 cursor-pointer items-center justify-center rounded-control border px-2 text-small tabular-nums transition-colors duration-150 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-teal ${
                  b.label === selected
                    ? "border-teal bg-teal/10 font-semibold text-fg"
                    : "border-control text-muted hover:border-teal/60"
                }`}
              >
                <input
                  type="radio"
                  name={group}
                  value={b.label}
                  checked={b.label === selected}
                  onChange={() => setSelected(b.label)}
                  className="sr-only"
                />
                {b.label}
              </label>
            ))}
          </div>

          <div className="mt-6 flex flex-wrap items-end gap-x-8 gap-y-3" aria-live="polite">
            <div>
              <p className="pk-small m-0 text-muted">Win rate, {band.label} band</p>
              <p className="pk-figure m-0">{pct(band.winRate)}</p>
            </div>
            <div>
              <p className="pk-small m-0 text-muted">Confidence interval</p>
              <p className="m-0 text-body font-semibold tabular-nums text-fg">
                {pct(band.ciLow)} to {pct(band.ciHigh)}
              </p>
            </div>
            <div>
              <p className="pk-small m-0 text-muted">Deals in band</p>
              <p className="m-0 text-body font-semibold tabular-nums text-fg">{band.deals}</p>
            </div>
          </div>
          <p className="pk-small m-0 mt-2 text-muted">
            {band.label === peak.label
              ? "This is the win point: the band with the highest win rate in the book."
              : `${points} points below the win point band (${peak.label}, ${pct(peak.winRate)}).`}
          </p>

          <div className="mt-5 flex items-end gap-2" aria-hidden>
            {data.bands.map((b) => (
              <div key={b.label} className="flex flex-1 flex-col items-center gap-1">
                <div className="relative flex h-24 w-full items-end justify-center">
                  <div
                    className={`w-full max-w-8 rounded-t-md ${b.label === selected ? "bg-teal" : "bg-muted/40"}`}
                    style={{ height: `${Math.round(b.winRate * 100)}%` }}
                  />
                </div>
                <span className="pk-micro text-muted">{b.label}</span>
              </div>
            ))}
          </div>
          <p className="pk-small m-0 mt-3 text-muted">
            In this synthetic book, win rate stops improving past the win point.
          </p>
        </fieldset>
      </Card>
    </div>
  );
}
