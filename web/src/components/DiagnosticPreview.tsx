// The one product mockup on the landing page. Data comes from the caller
// (page.tsx), which reads it straight out of the bundled
// src/data/sample-fallback.json snapshot, so every number here is real
// output of the diagnostic on the synthetic 2,000-deal sample, not a
// hand-typed illustration. Regenerate the snapshot (see src/lib/api.ts) and
// these figures update on their own.
"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import CountUp from "@/components/CountUp";
import { pct } from "@/lib/format";

const EASE = [0.22, 1, 0.36, 1] as const;

export type Band = { label: string; winRate: number; isReference: boolean };

export type DiagnosticPreviewData = {
  opportunities: number;
  bookedAcvWon: number;
  priceRealizationWon: number;
  avgDiscountWon: number;
  excessSegment: number;
  excessSegmentPct: number;
  winRate: number;
  bands: Band[];
};

function Bar({ band, index }: { band: Band; index: number }) {
  const reduce = useReducedMotion();
  const heightPct = Math.round(band.winRate * 100);
  return (
    <div className="flex flex-1 flex-col items-center">
      <div className="relative flex h-32 w-full items-end">
        {band.isReference ? (
          <div className="pointer-events-none absolute -top-5 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-md border border-coral/50 bg-bg/90 px-1.5 py-0.5 text-xs font-semibold text-coral shadow">
            win point
          </div>
        ) : null}
        {/* Bars climb from the baseline as the chart scrolls into view, so the
            win-rate curve reads as a motion, not a static picture. */}
        <motion.div
          className={`mx-auto w-full max-w-[28px] rounded-t-md ${
            band.isReference ? "bg-coral/70 ring-2 ring-coral/40" : "bg-teal/60"
          }`}
          initial={{ height: reduce ? `${heightPct}%` : 0 }}
          whileInView={{ height: `${heightPct}%` }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ duration: reduce ? 0 : 0.7, ease: EASE, delay: reduce ? 0 : index * 0.06 }}
          aria-label={`Win rate at ${band.label} discount: ${heightPct}%`}
        />
      </div>
      <div className="mt-1 whitespace-nowrap text-[10px] text-muted">{band.label}</div>
    </div>
  );
}

function Kpi({
  label,
  value,
  sub,
  accent = false,
}: {
  label: string;
  value: React.ReactNode;
  sub: string;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border p-3 ${
        accent ? "pk-upside-glow border-coral/30 bg-surface" : "border-mist bg-surface-2"
      }`}
    >
      <div className="text-xs font-semibold uppercase tracking-wider text-muted">
        {label}
      </div>
      <div
        className={`mt-0.5 text-xl font-bold tabular-nums ${
          accent ? "text-coral" : "text-fg"
        }`}
      >
        {value}
      </div>
      <div className="text-xs text-muted">{sub}</div>
    </div>
  );
}

export default function DiagnosticPreview({ data }: { data: DiagnosticPreviewData }) {
  return (
    <section aria-label="The diagnostic on the sample book" className="relative">
      <div className="text-center">
        <p className="text-xs font-semibold uppercase tracking-wider text-teal">
          Scroll to see it run
        </p>
        <h2 className="mt-2 text-2xl font-bold text-fg sm:text-3xl">The diagnostic</h2>
      </div>

      <div className="pk-card-3d mx-auto mt-6 max-w-4xl rounded-2xl border border-mist bg-bg p-1 shadow-xl shadow-navy/20">
        {/* faux browser chrome */}
        <div className="flex items-center gap-2 rounded-t-xl border-b border-mist bg-surface px-3 py-2">
          <span className="h-2.5 w-2.5 rounded-full bg-coral/60" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber" />
          <span className="h-2.5 w-2.5 rounded-full bg-teal/60" />
          <div className="ml-2 flex-1 truncate rounded-md border border-mist bg-bg px-2 py-0.5 text-xs text-muted">
            pricekeel.com/diagnostic
          </div>
        </div>

        {/* page content */}
        <div className="space-y-4 rounded-b-xl bg-surface p-5">
          <p className="text-center text-xs font-semibold uppercase tracking-wider text-teal">
            Real output of the engine on a synthetic 2,000-deal book
          </p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Kpi
              label="Booked value"
              value={<CountUp to={data.bookedAcvWon} format="moneyShort" />}
              sub={`${data.opportunities.toLocaleString()} opportunities`}
            />
            <Kpi
              label="Price realization"
              value={<CountUp to={data.priceRealizationWon} format="pct" />}
              sub={`avg discount ${pct(data.avgDiscountWon)}`}
            />
            <Kpi
              label="Gap to segment win point"
              value={<CountUp to={data.excessSegment} format="moneyShort" />}
              sub={`${pct(data.excessSegmentPct)} of booked`}
              accent
            />
            <Kpi
              label="Win rate"
              value={<CountUp to={data.winRate} format="pct" />}
              sub="won deals"
            />
          </div>

          {/* win curve */}
          <div className="rounded-lg border border-mist bg-surface-2 p-4">
            <div className="text-sm font-semibold text-fg">Win rate by discount band</div>
            <div className="flex items-end gap-1 pt-5">
              {data.bands.map((b, i) => (
                <Bar key={b.label} band={b} index={i} />
              ))}
            </div>
            <p className="mt-3 text-xs leading-5 text-muted">
              Discounts past the win point buy fewer wins, not more.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 text-center">
        <Link
          href="/sample"
          className="inline-flex items-center gap-1 text-sm font-semibold text-teal hover:underline"
        >
          Run it on the full sample &rarr;
        </Link>
      </div>
    </section>
  );
}
