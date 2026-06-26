import Link from "next/link";
import Reveal from "@/components/Reveal";
import HeroHeadline from "@/components/HeroHeadline";
import LeakageCalculator from "@/components/LeakageCalculator";
import DiagnosticPreview from "@/components/DiagnosticPreview";
import MethodologyStrip from "@/components/MethodologyStrip";
import TrustStrip from "@/components/TrustStrip";
import WhatYouGet from "@/components/WhatYouGet";
import FounderStrip from "@/components/FounderStrip";

// Static marketing landing. No API dependency, so it always loads fast.
export const dynamic = "force-static";

export default function Landing() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      {/* 1. Hero ------------------------------------------------------------ */}
      <Reveal>
        <section className="py-8 text-center">
          <HeroHeadline />
          {/* Audience chip — promoted from micro-eyebrow into a substantive
              subhead so the 'who is this for' answer is immediate. */}
          <div className="mt-4 flex justify-center">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-teal/40 bg-surface px-3 py-1 text-xs font-semibold text-teal">
              <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-teal" />
              For VP Pricing teams at $10 to 100M ARR usage-based B2B SaaS
            </span>
          </div>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-slate">
            Pricekeel reads your closed deals and shows where discounting buys
            wins, where it just gives money away, and the discount that earns the
            most on the next deal. No warehouse, no integration. One CSV.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/sample"
              className="rounded-lg bg-navy px-5 py-3 font-medium text-white transition hover:bg-navy/90"
            >
              Try it on sample data
            </Link>
            {/* Demoted to text-link weight per the audit — the gated path
                should not compete visually with the demo path. */}
            <Link
              href="/upload"
              className="text-sm font-medium text-muted underline-offset-4 hover:text-teal hover:underline"
            >
              Or run it on your own CSV →
            </Link>
          </div>
        </section>
      </Reveal>

      {/* 2. Product preview (NEW) ------------------------------------------ */}
      <Reveal inView>
        <section className="mt-12">
          <DiagnosticPreview />
        </section>
      </Reveal>

      {/* 2b. What it does + what you get, merged into one pillar grid so the
          four ideas are stated once instead of across two separate grids. */}
      <Reveal inView>
        <section className="mt-14">
          <WhatYouGet />
        </section>
      </Reveal>

      {/* 3. Leakage calculator. Honest two-number split (gross discount +
          above-policy slice), math shown, no invented recovery rate. The
          sample numbers already appear in DiagnosticPreview above, so we cut
          the previously-here stats strip. Full shareable version at
          /calculator. */}
      <Reveal inView>
        <section className="mt-14">
          <LeakageCalculator />
          <p className="mt-3 text-center text-sm text-muted">
            <Link href="/calculator" className="text-teal underline-offset-4 hover:underline">
              Open the full calculator →
            </Link>
          </p>
        </section>
      </Reveal>

      {/* 6. Methodology credibility (NEW) ---------------------------------- */}
      <Reveal inView>
        <section className="mt-14">
          <MethodologyStrip />
        </section>
      </Reveal>

      {/* 7. Stack strip — unchanged --------------------------------------- */}
      <Reveal inView>
        <section className="mt-14">
          <p className="text-center text-sm font-medium text-slate">
            Built for the stack you already run
          </p>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {[
              { name: "Salesforce", status: "csv" },
              { name: "HubSpot", status: "csv" },
              { name: "Stripe", status: "csv" },
              { name: "Zuora", status: "csv" },
              { name: "Snowflake", status: "phase3" },
              { name: "Google Sheets", status: "csv" },
            ].map((tool) => (
              <div
                key={tool.name}
                className="pk-card-3d flex flex-col items-center justify-center rounded-xl border border-mist bg-surface px-3 py-4 text-center"
              >
                <div className="text-sm font-semibold text-fg">{tool.name}</div>
                <div
                  className={`mt-1 text-[10px] font-medium uppercase tracking-wider ${
                    tool.status === "csv" ? "text-teal" : "text-amber"
                  }`}
                >
                  {tool.status === "csv" ? "via CSV today" : "Connector planned"}
                </div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-center text-xs text-muted">
            A CSV export covers every CRM and billing system today; native
            connectors are on the roadmap with the margin layer.
          </p>
        </section>
      </Reveal>

      {/* 8. Margin Enhancement teaser — kept ------------------------------ */}
      <Reveal inView>
        <section className="mt-14 overflow-hidden rounded-xl border border-teal/30 bg-surface p-6 shadow-sm">
          <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <span className="rounded-full border border-teal/40 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-teal">
                On the roadmap
              </span>
              <h2 className="mt-2 text-xl font-bold text-fg">Margin Enhancement</h2>
              <p className="mt-1 max-w-2xl text-sm text-muted">
                The planned next layer: connect contracts and CRM to surface
                margin across the whole book, including special pricing
                agreements, fixed discounts, renewal uplift left on the table,
                and price-floor breaches. Design partners shape the priority.
              </p>
            </div>
          </div>
        </section>
      </Reveal>

      {/* 8. Slim founder credibility strip. Single horizontal card with
          photo, name, role, three credibility chips, and a quiet "Connect
          on LinkedIn" link. The design-partner offer + DM/Email CTAs that
          used to live here moved to /contact and /pricing, where a hard
          sales ask is appropriate. The landing should not lead with one. */}
      <Reveal inView>
        <section className="mt-14">
          <FounderStrip />
        </section>
      </Reveal>

      {/* 9. Trust strip. */}
      <Reveal inView>
        <section className="mt-10">
          <TrustStrip />
        </section>
      </Reveal>
    </main>
  );
}
