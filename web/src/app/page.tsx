import Link from "next/link";
import Reveal from "@/components/Reveal";
import HeroHeadline from "@/components/HeroHeadline";
import DiagnosticPreview from "@/components/DiagnosticPreview";
import CrmWorkflowPreview from "@/components/CrmWorkflowPreview";
import MethodologyStrip from "@/components/MethodologyStrip";
import TrustStrip from "@/components/TrustStrip";
import WhatYouGet from "@/components/WhatYouGet";
import FounderStrip from "@/components/FounderStrip";

// Static marketing landing. No API dependency, so it always loads fast.
export const dynamic = "force-static";

export default function Landing() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      {/* One buyer, one problem, two honest next steps. */}
      <Reveal>
        <section className="py-10 text-center sm:py-14">
          <p className="mb-4 text-xs font-semibold uppercase tracking-[0.2em] text-teal">
            Salesforce deal guidance for B2B SaaS
          </p>
          <HeroHeadline />
          <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-slate sm:text-lg">
            Price every discount exception before approval. Pricekeel learns
            from closed Salesforce Opportunities, recommends a guardrail for
            the live deal, and records the decision with evidence Finance can audit.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/sample"
              className="rounded-lg bg-teal px-5 py-3 font-semibold text-bg transition hover:-translate-y-0.5 hover:bg-teal/90"
            >
              Explore a live sample
            </Link>
            <Link
              href="/contact"
              className="rounded-lg border border-mist bg-surface px-5 py-3 font-medium text-fg transition hover:border-teal"
            >
              Walk through one discount exception
            </Link>
          </div>
          <div className="mx-auto mt-8 flex max-w-3xl flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-muted">
            <span><strong className="font-semibold text-fg">Built for</strong> RevOps · Deal Desk · Pricing</span>
            <span><strong className="font-semibold text-fg">ICP</strong> $20–100M ARR · usage or hybrid SaaS</span>
            <span><strong className="font-semibold text-fg">Buyer</strong> CFO / Finance</span>
          </div>
        </section>
      </Reveal>

      <Reveal inView>
        <section className="mt-8">
          <CrmWorkflowPreview />
        </section>
      </Reveal>

      <Reveal inView>
        <section className="mt-16">
          <WhatYouGet />
        </section>
      </Reveal>

      <Reveal inView>
        <section className="mt-16">
          <DiagnosticPreview />
        </section>
      </Reveal>

      <Reveal inView>
        <section className="mt-16">
          <MethodologyStrip />
        </section>
      </Reveal>

      <Reveal inView>
        <section className="mt-16">
          <p className="text-center text-xs font-semibold uppercase tracking-[0.18em] text-teal">
            The evidence stack
          </p>
          <h2 className="mt-2 text-center text-xl font-bold text-fg sm:text-2xl">
            Start with CRM truth. Add context only where it is valid.
          </h2>
          <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { name: "Salesforce", status: "Native OAuth", detail: "Opportunity, Account, product, price, outcome, and approval context." },
              { name: "Public competitor sources", status: "Cited context", detail: "Pricing pages, releases, case studies, interviews, funding news, and investor calls." },
              { name: "Billing / ERP", status: "Required for margin", detail: "Cost data is a separate input. Pricekeel never labels a CRM proxy as true margin." },
              { name: "Product telemetry", status: "Required for application insight", detail: "Usage context extends recommendations only after the data contract is validated." },
            ].map((source) => (
              <div
                key={source.name}
                className="rounded-xl border border-mist bg-surface p-4"
              >
                <div className="text-[10px] font-semibold uppercase tracking-wider text-teal">{source.status}</div>
                <div className="mt-1 text-sm font-semibold text-fg">{source.name}</div>
                <p className="mt-2 text-xs leading-5 text-muted">{source.detail}</p>
              </div>
            ))}
          </div>
        </section>
      </Reveal>

      {/* 8. Evidence boundary ------------------------------------------------ */}
      <Reveal inView>
        <section className="mt-14 overflow-hidden rounded-xl border border-teal/30 bg-surface p-6 shadow-sm">
          <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <span className="rounded-full border border-teal/40 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-teal">
                V1 boundary
              </span>
              <h2 className="mt-2 text-xl font-bold text-fg">Discount intelligence from CRM evidence</h2>
              <p className="mt-1 max-w-2xl text-sm text-muted">
                Salesforce can support list-to-booked realization, win-rate
                patterns, and exception governance. True margin requires cost
                data from billing or ERP; application-level recommendations
                require product telemetry. Pricekeel does not infer either from
                CRM fields alone.
              </p>
            </div>
          </div>
        </section>
      </Reveal>

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

      <Reveal inView>
        <section className="mt-10 rounded-2xl border border-teal/40 bg-surface px-6 py-8 text-center sm:px-10">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal">Design-partner cohort</p>
          <h2 className="mt-2 text-2xl font-bold text-fg">Bring one real pricing exception.</h2>
          <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-muted">
            We will show how Pricekeel reads the Opportunity, builds the
            guardrail, adds cited competitor context, and records the decision.
            No Salesforce credentials are needed for the first walkthrough.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link href="/contact" className="rounded-lg bg-teal px-5 py-3 font-semibold text-bg hover:bg-teal/90">
              Request the walkthrough
            </Link>
            <Link href="/sample" className="rounded-lg border border-mist bg-surface-2 px-5 py-3 font-medium text-fg hover:border-teal">
              Explore the sample first
            </Link>
          </div>
        </section>
      </Reveal>
    </main>
  );
}
