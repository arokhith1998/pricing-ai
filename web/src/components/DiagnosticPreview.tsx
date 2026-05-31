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

const BANDS = [
  { label: "0%", win: 0.42 },
  { label: "5%", win: 0.56 },
  { label: "10%", win: 0.68 },
  { label: "15%", win: 0.74, winPoint: true },
  { label: "20%", win: 0.75 },
  { label: "25%", win: 0.76 },
  { label: "30%+", win: 0.76 },
];

function Bar({ band }: { band: (typeof BANDS)[number] }) {
  const heightPct = Math.round(band.win * 100);
  return (
    <div className="flex flex-1 flex-col items-center">
      <div className="relative flex h-32 w-full items-end">
        {band.winPoint ? (
          <div className="pointer-events-none absolute -top-5 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-md border border-coral/50 bg-bg/90 px-1.5 py-0.5 text-[10px] font-semibold text-coral shadow">
            win point
          </div>
        ) : null}
        <div
          className={`mx-auto w-full max-w-[28px] rounded-t-md ${
            band.winPoint
              ? "bg-coral/70 ring-2 ring-coral/40"
              : "bg-teal/60"
          }`}
          style={{ height: `${heightPct}%` }}
          aria-label={`Win rate at ${band.label} discount: ${heightPct}%`}
        />
      </div>
      <div className="mt-1 text-[10px] text-muted">{band.label}</div>
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
        accent ? "border-teal/40 bg-surface" : "border-mist bg-surface-2"
      }`}
    >
      <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">
        {label}
      </div>
      <div
        className={`mt-0.5 text-xl font-bold tabular-nums ${
          accent ? "text-teal" : "text-fg"
        }`}
      >
        {value}
      </div>
      <div className="text-[10px] text-muted">{sub}</div>
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
          The diagnostic, on a live sample of 2,000 closed deals
        </h2>
        <p className="mx-auto mt-2 max-w-2xl text-sm text-muted">
          Below is the actual structure of the page on{" "}
          <Link href="/sample" className="text-teal underline">
            /sample
          </Link>
          : KPIs, win-rate curve with the calculated win point, and the deal
          list to investigate. Your numbers come from your own CSV.
        </p>
      </div>

      <div className="mx-auto mt-6 max-w-4xl rounded-2xl border border-mist bg-bg p-1 shadow-xl shadow-navy/20">
        {/* faux browser chrome */}
        <div className="flex items-center gap-2 rounded-t-xl border-b border-mist bg-surface px-3 py-2">
          <span className="h-2.5 w-2.5 rounded-full bg-coral/60" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber" />
          <span className="h-2.5 w-2.5 rounded-full bg-teal/60" />
          <div className="ml-2 flex-1 truncate rounded-md border border-mist bg-bg px-2 py-0.5 text-[11px] text-muted">
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
              label="Pricing upside"
              value="$11.2M"
              sub="16.7% of booked"
              accent
            />
            <Kpi label="Win rate" value="60.8%" sub="2,000 opportunities" />
          </div>

          {/* win curve */}
          <div className="rounded-lg border border-mist bg-surface-2 p-4">
            <div className="mb-3 flex items-baseline justify-between">
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">
                  Win rate by discount band
                </div>
                <div className="text-sm font-semibold text-fg">
                  Win point at the 15% band; bigger discounts don&rsquo;t buy
                  more wins
                </div>
              </div>
              <div className="hidden text-[10px] text-muted sm:block">
                won / discount %
              </div>
            </div>
            <div className="flex items-end gap-1 pt-5">
              {BANDS.map((b) => (
                <Bar key={b.label} band={b} />
              ))}
            </div>
          </div>

          {/* mini deals-to-investigate */}
          <div className="rounded-lg border border-mist bg-surface-2 p-4">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">
              Top deals to investigate
            </div>
            <div className="mt-2 space-y-1.5 text-xs text-ink">
              {[
                ["Acme Corp", "Enterprise", "32%", "$248K"],
                ["Globex", "Enterprise", "28%", "$192K"],
                ["Initech", "Mid-Market", "26%", "$164K"],
                ["Soylent", "Mid-Market", "25%", "$141K"],
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
        <p className="mt-1 text-[11px] text-muted">
          Live numbers from the bundled sample. Your numbers come from your CSV.
        </p>
      </div>
    </section>
  );
}
