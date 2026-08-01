import { Suspense } from "react";
import Link from "next/link";
import { cookies } from "next/headers";
import { getDemoWithFallback, type Diagnostic } from "@/lib/api";
import { money, pct } from "@/lib/format";
import { LEAD_COOKIE, verifyLeadCookieValue } from "@/lib/auth";
import Summary from "@/components/Summary";
import Reveal from "@/components/Reveal";
import ApiError from "@/components/ApiError";
import LeadForm from "@/components/LeadForm";
import MagicLinkForm from "@/components/MagicLinkForm";
import CountUp from "@/components/CountUp";
import PageGuide from "@/components/PageGuide";

export const dynamic = "force-dynamic";

function MetricCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: React.ReactNode;
  sub?: string;
  accent?: "navy" | "coral";
}) {
  return (
    <div
      className={`pk-fade-in pk-card-3d rounded-xl border bg-surface p-5 shadow-sm ${
        accent === "coral" ? "pk-upside-static border-coral/30" : "border-mist"
      }`}
    >
      <div className="text-sm text-slate">{label}</div>
      <div
        className={`mt-1 text-3xl font-bold tabular-nums ${accent === "coral" ? "text-coral" : "text-fg"}`}
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
          <div className="rounded-lg border border-mist bg-surface px-3 py-2">
            <div className="text-sm font-semibold text-fg">{title}</div>
            <div className="text-xs text-slate">{sub}</div>
          </div>
          {i < STEPS.length - 1 ? <span className="text-slate">&rarr;</span> : null}
        </div>
      ))}
    </div>
  );
}

// Whitelist of routes that proxy.ts can attach as `?unlock=`. Anything else
// is treated as no requested path so we never bounce a user to a route the
// gate doesn't actually cover.
const UNLOCK_TARGETS: Record<string, string> = {
  diagnostic: "/diagnostic",
  guidance: "/guidance",
};

function unlockLabel(slug: string): string {
  return slug.charAt(0).toUpperCase() + slug.slice(1);
}

function UnlockBanner({ unlock }: { unlock: string }) {
  const label = unlockLabel(unlock);
  return (
    <section
      role="status"
      aria-live="polite"
      className="rounded-xl border border-teal/50 bg-teal/5 px-5 py-4"
    >
      <div className="flex items-start gap-3">
        <span aria-hidden className="mt-0.5 text-teal">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </span>
        <div className="min-w-0 text-sm">
          <div className="font-semibold text-fg">
            <span className="text-teal">{label}</span> is gated behind one form
          </div>
          <p className="mt-0.5 text-muted">
            Fill the unlock form below (company email, ~20 seconds). We will
            open <span className="font-medium text-ink">{UNLOCK_TARGETS[unlock]}</span>{" "}
            automatically the moment you submit.
          </p>
        </div>
      </div>
    </section>
  );
}

function FlashBanner({ flash }: { flash: string }) {
  // Tiny flash for the /api/lead/redeem failure paths so the visitor knows
  // why we sent them back here instead of opening their gated route.
  const msg =
    flash === "link_expired"
      ? "That access link expired. Request a new one below, or fill the form."
      : "That access link did not check out. Request a new one below, or fill the form.";
  return (
    <section
      role="status"
      aria-live="polite"
      className="rounded-xl border border-coral/50 bg-coral/5 px-5 py-3 text-sm text-fg"
    >
      <span className="font-semibold text-coral">Heads up.</span> {msg}
    </section>
  );
}

function LeadGate({
  leak,
  unlock,
}: {
  leak: Diagnostic["leakage"];
  unlock?: string;
}) {
  const nextRoute = unlock ? UNLOCK_TARGETS[unlock] : undefined;
  return (
    <section className="rounded-xl border border-mist bg-surface p-6 shadow-sm">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h2 className="text-lg font-semibold text-fg">
            Unlock the full diagnostic
          </h2>
          <p className="mt-1 text-sm text-slate">
            That is {money(leak.excess_vs_reference_won)} of revenue discounted
            past the point that wins anything: pricing upside to pursue. The
            full read-out shows where it is and what to do:
          </p>
          <ul className="mt-3 space-y-1.5 text-sm text-ink">
            <li>• A written executive summary</li>
            <li>• Win rate vs discount, and the win point</li>
            <li>• Price realization by segment and governance gaps</li>
            <li>• Per-deal discount guidance with a plain &ldquo;why&rdquo;</li>
          </ul>
        </div>
        <div className="rounded-lg bg-surface-2 p-4">
          <LeadForm next={nextRoute ?? "/diagnostic"} />
          <MagicLinkForm next={nextRoute ?? "/diagnostic"} />
        </div>
      </div>
    </section>
  );
}

function FullSample() {
  return (
    <>
      <PageGuide
        title="A worked example. Focus on the coral upside number first."
        body="We ran the diagnostic on a 2,000-deal synthetic book so you can see the shape of the analysis before sending your own data. Read the cards above, skim the summary, then open the Diagnostic or Guidance tabs for the deep view."
        bullets={[
          "The coral 'Pricing upside to pursue' card is the headline number worth a meeting.",
          "The Diagnostic tab shows where it concentrates by segment, BU, and product line.",
          "The Guidance tab picks a single deal and recommends a discount with a plain why.",
        ]}
      />

      <Reveal inView>
        <section className="rounded-xl border border-mist bg-surface p-5 shadow-sm">
          <h2 className="mb-2 text-lg font-semibold text-fg">Executive summary</h2>
          <Suspense
            fallback={
              <p className="animate-pulse text-sm text-slate">Writing the summary&hellip;</p>
            }
          >
            <Summary />
          </Suspense>
        </section>
      </Reveal>

      <Reveal inView>
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Link
            href="/diagnostic"
            className="pk-card-3d rounded-xl border border-mist bg-surface p-5 shadow-sm hover:border-teal"
          >
            <div className="text-lg font-semibold text-fg">Diagnostic →</div>
            <p className="mt-1 text-sm text-slate">
              Win rate vs discount, leakage lenses, quarter-end, governance, and the
              deals to look at first.
            </p>
          </Link>
          <Link
            href="/guidance"
            className="pk-card-3d rounded-xl border border-mist bg-surface p-5 shadow-sm hover:border-teal"
          >
            <div className="text-lg font-semibold text-fg">Guidance →</div>
            <p className="mt-1 text-sm text-slate">
              Pick a deal and see the discount that maximizes expected value, with a
              plain-language why.
            </p>
          </Link>
        </section>
      </Reveal>

      <Reveal inView>
        <section>
          <h2 className="mb-3 text-lg font-semibold text-fg">How it works</h2>
          <Flow />
        </section>
      </Reveal>
    </>
  );
}

export default async function SamplePage({
  searchParams,
}: {
  // Next 16 (App Router): searchParams is async. proxy.ts attaches
  // ?unlock=<diagnostic|guidance> when it redirects a
  // gated route here; we surface that as a banner + redirect-on-success.
  searchParams: Promise<{ unlock?: string; flash?: string }>;
}) {
  const unlocked = await verifyLeadCookieValue(
    (await cookies()).get(LEAD_COOKIE)?.value,
  );
  const { unlock, flash } = await searchParams;
  const validUnlock =
    unlock && Object.prototype.hasOwnProperty.call(UNLOCK_TARGETS, unlock)
      ? unlock
      : undefined;
  const validFlash =
    flash === "link_expired" || flash === "link_invalid" ? flash : undefined;

  // Prefer the live API; fall back to the bundled snapshot of the same demo
  // payload when the engine is unreachable, with an honest note below. The
  // error page is the last resort only.
  let d: Diagnostic;
  let cached = false;
  try {
    ({ data: d, cached } = await getDemoWithFallback());
  } catch {
    return <ApiError />;
  }
  const o = d.overview;
  const l = d.leakage;

  return (
    <main className="mx-auto max-w-6xl space-y-8 px-6 py-8">
      {!unlocked && validFlash ? <FlashBanner flash={validFlash} /> : null}
      {!unlocked && validUnlock ? <UnlockBanner unlock={validUnlock} /> : null}
      <div>
        <p className="text-sm font-medium text-teal">Sample data</p>
        <h1 className="text-2xl font-bold text-fg">
          Where the money goes, and what to do about it
        </h1>
        <p className="mt-1 text-slate">
          A worked example on a realistic synthetic book of 2,000 closed deals.
        </p>
        {cached ? (
          <p className="mt-2 inline-block rounded-md border border-mist bg-surface px-2 py-1 text-xs text-muted">
            Cached sample: the live analysis engine is briefly unavailable, so
            these figures come from a bundled snapshot of the same dataset.
          </p>
        ) : null}
      </div>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Booked value (annual)"
          value={<CountUp to={o.booked_acv_won} format="money" />}
        />
        <MetricCard
          label="Price realization"
          value={<CountUp to={o.price_realization_won} format="pct" />}
          sub={`Average discount ${pct(o.avg_discount_won)}`}
        />
        <MetricCard
          label="Pricing upside to pursue"
          value={<CountUp to={l.excess_vs_reference_won} format="money" />}
          sub={`${pct(l.excess_pct_of_booked)} of booked value, discounted past the win point`}
          accent="coral"
        />
        <MetricCard
          label="Win rate"
          value={<CountUp to={o.win_rate} format="pct" />}
          sub={`${o.won.toLocaleString()} won, ${o.lost.toLocaleString()} lost`}
        />
      </section>

      {unlocked ? <FullSample /> : <LeadGate leak={l} />}
    </main>
  );
}
