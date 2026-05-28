import Link from "next/link";
import Reveal from "@/components/Reveal";

// Static marketing landing — no API dependency, so it always loads fast.
export const dynamic = "force-static";

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-xl border border-mist bg-surface p-5 text-center shadow-sm">
      <div className="text-3xl font-extrabold tabular-nums text-fg">{value}</div>
      <div className="mt-1 text-sm text-slate">{label}</div>
    </div>
  );
}

function Capability({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-mist bg-surface p-5 shadow-sm">
      <h3 className="font-semibold text-fg">{title}</h3>
      <p className="mt-1 text-sm text-slate">{body}</p>
    </div>
  );
}

export default function Landing() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <Reveal>
        <section className="py-8 text-center">
          <p className="text-sm font-semibold uppercase tracking-wide text-teal">
            Pricing intelligence for usage-based B2B SaaS
          </p>
          <h1 className="mx-auto mt-3 max-w-3xl text-4xl font-extrabold tracking-tight text-fg sm:text-5xl">
            Stop giving away price that wins you nothing.
          </h1>
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
            <Link
              href="/upload"
              className="rounded-lg border border-mist bg-surface px-5 py-3 font-medium text-fg transition hover:border-teal"
            >
              Run it on your data
            </Link>
          </div>
        </section>
      </Reveal>

      <Reveal delay={0.05}>
        <section className="mt-10">
          <p className="text-center text-sm font-medium text-slate">
            The pricing upside hiding in a typical book of deals
          </p>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Stat value="10–20%" label="of list price given up to discounting" />
            <Stat value="~17%" label="of booked value discounted past the point that wins anything" />
            <Stat value="1 in 4" label="off-policy deals closed with no recorded approver" />
          </div>
          <p className="mt-2 text-center text-xs text-slate">
            Figures from the bundled sample. Your numbers come from your own data.
          </p>
        </section>
      </Reveal>

      <Reveal delay={0.05}>
        <section className="mt-12">
          <h2 className="text-center text-xl font-bold text-fg">What it does</h2>
          <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
            <Capability
              title="Find the leakage"
              body="Price realization, win rate by discount band, and three views of discount leakage from a plain description to the strongest claim worth acting on."
            />
            <Capability
              title="Find the win point"
              body="The discount level where win rate stops improving. Everything given beyond it is a list to investigate, not a refund."
            />
            <Capability
              title="Guide the next discount"
              body="A win-probability model recommends the discount that maximizes expected value on a given deal, with a plain-language why."
            />
          </div>
        </section>
      </Reveal>

      <Reveal delay={0.05}>
        <section className="mt-12">
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
                className="flex flex-col items-center justify-center rounded-xl border border-mist bg-surface px-3 py-4 text-center"
              >
                <div className="text-sm font-semibold text-fg">{tool.name}</div>
                <div
                  className={`mt-1 text-[10px] font-medium uppercase tracking-wider ${
                    tool.status === "csv" ? "text-teal" : "text-amber"
                  }`}
                >
                  {tool.status === "csv" ? "via CSV today" : "Phase 3 connector"}
                </div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-center text-xs text-muted">
            A CSV export covers every CRM and billing system today; native
            connectors land with the Phase 3 margin layer.
          </p>
        </section>
      </Reveal>

      <Reveal delay={0.05}>
        <section className="mt-12 overflow-hidden rounded-xl border border-teal/30 bg-surface p-6 shadow-sm">
          <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <span className="rounded-full border border-teal/40 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-teal">
                Final phase · coming soon
              </span>
              <h2 className="mt-2 text-xl font-bold text-fg">Margin Enhancement</h2>
              <p className="mt-1 max-w-2xl text-sm text-muted">
                Next, Pricekeel connects to your contracts and CRM to find margin
                across the whole book: special pricing agreements, fixed
                discounts, renewal uplift left on the table, and price-floor
                breaches. From a retrospective diagnostic to a live margin engine.
              </p>
            </div>
            <span className="shrink-0 text-3xl">📈</span>
          </div>
        </section>
      </Reveal>

      <Reveal delay={0.05}>
        <section className="mt-8 rounded-xl border border-mist bg-surface p-6 text-center shadow-sm">
          <h2 className="text-lg font-semibold text-fg">See it on your own deals</h2>
          <p className="mx-auto mt-1 max-w-xl text-sm text-slate">
            Export a CSV of your closed opportunities and get your own diagnostic.
            Your data is processed to produce the analysis and is not stored. If
            you need an NDA first, we will sign one.
          </p>
          <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/sample"
              className="rounded-lg bg-navy px-5 py-3 font-medium text-white transition hover:bg-navy/90"
            >
              Start with the sample
            </Link>
            <Link
              href="/upload"
              className="rounded-lg border border-mist bg-surface px-5 py-3 font-medium text-fg transition hover:border-teal"
            >
              Upload your CSV
            </Link>
          </div>
        </section>
      </Reveal>
    </main>
  );
}
