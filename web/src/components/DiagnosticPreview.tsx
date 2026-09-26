// Static low-fidelity preview of /diagnostic, rendered with the real sample
// figures so visitors see the actual product structure before clicking.
// Designed to be swap-replaced with a real screen capture when you have one;
// until then, this avoids needing image files in the repo.
//
// The visual treatment mimics a browser window with the live URL and the same
// KPI/chart/table layout the real /diagnostic page uses, with three callout
// labels pointing at the things a buyer wants to see first.
//
// All numbers below come from the bundled synthetic 2,000-deal sample and
// match what /sample produces on first load.
"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";

const EASE = [0.22, 1, 0.36, 1] as const;

// Win-rate-by-band figures from the real demo payload (policy 0.15), rounded
// to the nearest point. Win point = the 5-10% band (reference threshold 5%):
// win rate peaks there at ~68% and then flattens and falls. Regenerate by
// dumping pricing.diagnostic.run on data/synthetic/deals.csv if the sample
// dataset changes.
const BANDS = [
  { label: "0-5%", win: 0.54 },
  { label: "5-10%", win: 0.68, winPoint: true },
  { label: "10-15%", win: 0.66 },
  { label: "15-20%", win: 0.62 },
  { label: "20-25%", win: 0.58 },
  { label: "25%+", win: 0.42 },
];

function Bar({ band, index }: { band: (typeof BANDS)[number]; index: number }) {
  const reduce = useReducedMotion();
  const heightPct = Math.round(band.win * 100);
  return (
    <div className="flex flex-1 flex-col items-center">
      <div className="relative flex h-32 w-full items-end">
        {band.winPoint ? (
          <div className="pointer-events-none absolute -top-5 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-md border border-coral/50 bg-bg/90 px-1.5 py-0.5 text-xs font-semibold text-coral shadow">
            win point
          </div>
        ) : null}
        {/* Bars climb from the baseline as the chart scrolls into view, so the
            win-rate curve reads as a motion, not a static picture. */}
        <motion.div
          className={`mx-auto w-full max-w-[28px] rounded-t-md ${
            band.winPoint
              ? "bg-coral/70 ring-2 ring-coral/40"
              : "bg-teal/60"
          }`}
          initial={{ height: reduce ? `${heightPct}%` : 0 }}
          whileInView={{ height: `${heightPct}%` }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ duration: reduce ? 0 : 0.7, ease: EASE, delay: reduce ? 0 : index * 0.06 }}
          aria-label={`Win rate at ${band.label} discount: ${heightPct}%`}
        />
      </div>
      <div className="mt-1 text-xs text-muted">{band.label}</div>
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
  value: string;
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

export default function DiagnosticPreview() {
  return (
    <section aria-label="What the diagnostic looks like" className="relative">
      <div className="text-center">
        <p className="text-xs font-semibold uppercase tracking-wider text-teal">
          What you see when you click
        </p>
        <h2 className="mt-2 text-2xl font-bold text-fg sm:text-3xl">
          The diagnostic, on a synthetic sample of 2,000 closed deals
        </h2>
        <p className="mx-auto mt-2 max-w-2xl text-sm text-muted">
          Below is the actual structure of the page on{" "}
          <Link href="/sample" className="text-teal underline">
            /sample
          </Link>
          : KPIs, win-rate curve with the calculated win point, and the deal
          list to investigate. In the connected workflow, these numbers come
          from live Salesforce Opportunity history.
        </p>
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
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Kpi
              label="Booked value"
              value="$67.1M"
              sub="1,215 won deals"
            />
            <Kpi
              label="Price realization"
              value="81.4%"
              sub="avg discount 13.8%"
            />
            <Kpi
              label="Gap to segment reference win point"
              value="$8.9M"
              sub="Pilot tests actual recovery · 13.3% of booked"
              accent
            />
            <Kpi label="Win rate" value="60.8%" sub="2,000 opportunities" />
          </div>
          <p className="text-xs leading-4 text-muted">
            Price realization is dollar-weighted on won deals; average
            discount is deal-count-weighted, so the two figures differ by
            design.
          </p>

          {/* win curve */}
          <div className="rounded-lg border border-mist bg-surface-2 p-4">
            <div className="mb-3 flex items-baseline justify-between">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Win rate by discount band
                </div>
                <div className="text-sm font-semibold text-fg">
                  Win point at the 5 to 10% band; bigger discounts don&rsquo;t
                  buy more wins
                </div>
              </div>
              <div className="hidden text-xs text-muted sm:block">
                won / discount %
              </div>
            </div>
            <div className="flex items-end gap-1 pt-5">
              {BANDS.map((b, i) => (
                <Bar key={b.label} band={b} index={i} />
              ))}
            </div>
          </div>

          {/* mini deals-to-investigate */}
          <div className="rounded-lg border border-mist bg-surface-2 p-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted">
              Top deals to investigate
            </div>
            <div className="mt-2 space-y-1.5 text-xs text-ink">
              {[
                // Top of top_leak_deals from the same demo payload (rounded).
                ["Lattice AI Corp.", "Enterprise", "40%", "$188K"],
                ["Cobalt AI Inc.", "Enterprise", "27%", "$121K"],
                ["Initech Systems Inc", "Enterprise", "36%", "$106K"],
                ["Fathom Digital LLC", "Enterprise", "24%", "$106K"],
              ].map(([account, segment, discount, leak]) => (
                <div
                  key={account}
                  className="grid grid-cols-4 gap-2 rounded border border-mist bg-bg px-2 py-1.5"
                >
                  <span className="truncate font-medium text-fg">{account}</span>
                  <span className="truncate text-muted">{segment}</span>
                  <span className="text-coral">−{discount}</span>
                  <span className="text-right tabular-nums text-fg">{leak}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 text-center">
        <Link
          href="/sample"
          className="inline-flex items-center gap-1 text-sm font-semibold text-teal hover:underline"
        >
          See the full diagnostic on the sample data →
        </Link>
        <p className="mt-1 text-xs text-muted">
          Illustrative figures from a synthetic 2,000-deal sample; not
          customer data. Your workspace reads Salesforce; CSV/XLSX remains
          available for onboarding and other CRMs.
        </p>
      </div>
    </section>
  );
}
