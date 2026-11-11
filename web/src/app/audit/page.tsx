import { Button, Card, Eyebrow, PageHeader, Section } from "@/components/ui";
import { BOTTLENECKS } from "@/components/landing/Bottlenecks";
import { pageMetadata } from "@/lib/page-metadata";
import { AUDIT_DAYS, AUDIT_DELIVERY_GUARANTEE, AUDIT_FOLLOW_ON, AUDIT_PRICE, COST_BASIS_LABEL } from "@/lib/audit-offer";

export const dynamic = "force-static";
export const metadata = pageMetadata({
  title: "14-day pricing audit",
  description:
    "A done-for-you 14-day pricing audit for AI companies: which customers and plans cost more to serve than they pay, and a packaging fix to decide on.",
  path: "/audit",
});

// The six audit questions, one set per bottleneck (ids match Bottlenecks.tsx).
// Source: gtm/ai-margin-audit-offer.md. Some answers are evidence-backed from
// the customer's numbers and some are judgement; the deliverables say which.
const QUESTIONS: Record<string, string[]> = {
  "cost-floor": [
    "What does it cost to serve each customer per month: model inference, storage and hosting?",
    "Which customers and plans pay less than they cost, and how concentrated is cost in a small heavy-user tail?",
    "At what usage does each plan stop covering its own cost?",
  ],
  packaging: [
    "Where does the current structure leave money uncollected or customers exposed to surprise bills?",
    "How much does each customer's monthly bill move, and would your buyers accept a commit, a cap or a band?",
    "If seats stop being the unit, what happens to revenue as the product gets more effective?",
  ],
  "value-metric": [
    "Which unit tracks both the value your customers get and your cost?",
    "If you priced per outcome, how lumpy would revenue be, and can the outcome be defined in a contract today?",
    "Are discounts given to win early accounts still sitting in your price book?",
  ],
  variance: [
    "Where do inconsistent outputs show up in the commercial record: credits, refunds, re-runs, churn reasons?",
    "How much human effort sits behind delivery, and is it priced?",
  ],
  pilots: [
    "How much reported recurring revenue comes from pilots or paid trials?",
    "Of the pilots that ended, how many converted, and at what price relative to the pilot?",
    "What does ARR look like with pilot revenue separated out?",
  ],
  bundling: [
    "Which of your features could a large incumbent bundle into an existing suite?",
    "Which parts of your price depend on being a stand-alone add-on, and which on owning the workflow and your customers' history?",
  ],
};

const DELIVERABLES: string[] = [
  `A per-customer table: plan, monthly revenue, attributed cost, ${COST_BASIS_LABEL}, a health band and a confidence rating for how the cost was attributed. Cost you cannot attribute to a customer is shown as an unallocated line, and if more than one fifth of cost cannot be attributed, the readout says the figures are an upper bound.`,
  "A plan-level cost floor: for each plan, the usage level at which it stops covering its cost.",
  "A heavy-user tail analysis: share of cost by customer decile, and who sits in the tail.",
  "A list of accounts that cost more than they pay, with the drivers for each, and how the conclusion changes under different cost allocations.",
  "An optimized packaging structure, as a recommendation for you to decide on: one primary structure and two alternatives, each shown against your own history as a static re-pricing table. It is not a forecast and does not model how customers would react.",
  "A predictability review: month-to-month bill variance by customer, and where a commit, cap or band would reduce it.",
  "A discount and packaging review: concessions in the price book and on invoices, and what they cost.",
  "A pilot-to-ARR view: revenue split into pilot and recurring, conversion of ended pilots, and ARR restated with pilot revenue separated.",
  "Variance, trust and bundling notes: evidence-backed where your records allow, labelled as judgement where they do not.",
  "A 60-minute readout with your numbers first, and a written PDF you can forward to your finance lead or board.",
  "A method appendix with every formula, assumption and judgement call, so your finance lead can audit the work rather than trust it.",
  "A written data-deletion certification at the end of the engagement.",
];

const EXPORTS: string[] = [
  "Billing exports",
  "Model-provider usage and cost exports",
  "Cloud and storage cost lines",
  "A customer list with plan and start date",
  "Your pricing page and packaging history",
];

const GATE: string[] = [
  "Counsel has signed the data-addendum amendment covering per-customer cost.",
  "Our legal entity is formed.",
  "Our insurance is bound.",
  "An engagement letter is signed.",
];

const NOT_FOR: string[] = [
  "Companies with fewer than about 10 billed customers or under 3 months of billing history.",
  "Companies that cannot attribute any model or hosting cost to customers and will not instrument it. We can run a plan-level view, but not the per-customer table.",
  "Anyone who wants a guaranteed recovery of revenue, or a tool they can log into. This is a done-for-you analysis delivered by a person, not software.",
  "Companies whose main cost is owned GPU capacity that cannot be allocated to customers.",
  "Teams that want us to hold API keys or connect to their systems. We work from exports.",
  "Anyone unwilling to sign the NDA and data addendum.",
];

export default function AuditPage() {
  return (
    <main id="main" tabIndex={-1} className="outline-none">
      <Section>
        <PageHeader
          eyebrow={`${AUDIT_DAYS}-day pricing audit`}
          title="Find which customers cost you more than they pay."
          lead={`In ${AUDIT_DAYS} days from validated intake of your billing and cost exports, we show you which customers and plans your inference and storage costs leave with thin or negative ${COST_BASIS_LABEL}, and we recommend a packaging structure for you to decide on.`}
          actions={
            <Button href="/contact" size="lg">
              Request the audit
            </Button>
          }
        />
        <p className="pk-body mt-4 max-w-prose text-muted">
          No guarantee of recovered revenue. The audit is analytical and advisory, built on your
          historical data. Every pricing decision stays with you.
        </p>
      </Section>

      <Section band="band" labelledBy="audited-h">
        <Eyebrow>What we audit</Eyebrow>
        <h2 id="audited-h" className="pk-h2 m-0 mt-2">
          Six questions, one for each way AI pricing breaks.
        </h2>
        <p className="pk-body mt-3 max-w-prose text-muted">
          Some answers are evidence-backed from your numbers and some are judgement. The
          deliverables say which is which.
        </p>
        <ol className="m-0 mt-8 grid list-none grid-cols-1 gap-4 p-0 md:grid-cols-2">
          {BOTTLENECKS.map((b, i) => (
            <li key={b.id} data-question={b.id} className="flex">
              <Card className="w-full">
                <span className="pk-small font-semibold tabular-nums text-teal">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <h3 className="pk-h3 m-0 mt-1">{b.name}</h3>
                <ul className="pk-body m-0 mt-3 list-disc space-y-2 pl-5 text-muted marker:text-teal">
                  {QUESTIONS[b.id].map((q) => (
                    <li key={q}>{q}</li>
                  ))}
                </ul>
              </Card>
            </li>
          ))}
        </ol>
      </Section>

      <Section labelledBy="get-h">
        <Eyebrow>What you get</Eyebrow>
        <h2 id="get-h" className="pk-h2 m-0 mt-2">
          What you have in {AUDIT_DAYS} days.
        </h2>
        <ol className="pk-body mt-6 max-w-prose list-decimal space-y-3 pl-6 text-muted marker:text-teal">
          {DELIVERABLES.map((d) => (
            <li key={d}>{d}</li>
          ))}
        </ol>
      </Section>

      <Section band="band" labelledBy="need-h">
        <Eyebrow>What we need</Eyebrow>
        <h2 id="need-h" className="pk-h2 m-0 mt-2">
          Exports, a declaration and a key map.
        </h2>
        <ul className="pk-body mt-6 max-w-prose list-disc space-y-2 pl-5 text-muted marker:text-teal">
          {EXPORTS.map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
        <p className="pk-body mt-5 max-w-prose text-muted">
          We ask for exports only. No API keys, no OAuth tokens, no prompts or model outputs, and
          no end-user personal data. Customers appear as codes you assign.
        </p>
        <p className="pk-body mt-3 max-w-prose text-muted">
          You also confirm in writing, once per upload, that the cost file is your own cost of
          serving (the upload declaration), and you give us a key map from each cost key to a
          billing account. Without the declaration, no per-customer figure is produced. We
          also need one person on your side who can answer pricing questions and who owns the
          pricing decision.
        </p>
      </Section>

      <Section labelledBy="gate-h">
        <Eyebrow>The gate</Eyebrow>
        <h2 id="gate-h" className="pk-h2 m-0 mt-2">
          Before we can accept any file.
        </h2>
        <p className="pk-body mt-3 max-w-prose text-muted">
          We do not receive any customer cost file until all four of these are in place:
        </p>
        <ol className="pk-body mt-4 max-w-prose list-decimal space-y-2 pl-6 text-muted marker:text-teal">
          {GATE.map((g) => (
            <li key={g}>{g}</li>
          ))}
        </ol>
        <p className="pk-body mt-4 max-w-prose text-muted">
          Until then we can talk, which needs none of it. We will tell you when each is
          done.
        </p>
      </Section>

      <Section band="band" labelledBy="price-h">
        <Eyebrow>Price and clock</Eyebrow>
        <h2 id="price-h" className="pk-h2 m-0 mt-2">
          {AUDIT_PRICE} fixed, paid upfront.
        </h2>
        <p className="pk-body mt-3 max-w-prose font-medium text-fg" data-testid="delivery-guarantee">
          {AUDIT_DELIVERY_GUARANTEE}
        </p>
        <p className="pk-body mt-2 max-w-prose text-muted" data-testid="follow-on">
          {AUDIT_FOLLOW_ON}
        </p>
        <ul className="pk-body mt-6 max-w-prose list-disc space-y-3 pl-5 text-muted marker:text-teal">
          <li>
            <span className="font-medium text-fg">The {AUDIT_DAYS}-day clock starts at validated
            intake.</span>{" "}
            That is the day we receive the minimum set of exports and they pass our one-business-day
            readiness check. If they do not pass, we tell you what is missing and the clock has not
            started.
          </li>
          <li>
            <span className="font-medium text-fg">No share of results, no success fee.</span> There
            is no credit toward a later subscription on the first two audits.
          </li>
          <li>
            <span className="font-medium text-fg">Mutual NDA and data addendum</span> are signed
            before any data moves.
          </li>
          <li>
            <span className="font-medium text-fg">Your data is used only to deliver your audit.</span>{" "}
            It is not used to improve models that benefit other customers without your prior
            written consent. It is deleted within 30 days of engagement end, with written
            certification.
          </li>
          <li>
            <span className="font-medium text-fg">Benchmarking is opt-in and off by default.</span>{" "}
            The audit is identical either way.
          </li>
          <li>
            <span className="font-medium text-fg">We recommend, you decide.</span> Findings are
            historical and correlational, and everything in the readout traces back to a documented
            formula and your own rows.
          </li>
        </ul>
      </Section>

      <Section labelledBy="who-h">
        <Eyebrow>Fit</Eyebrow>
        <h2 id="who-h" className="pk-h2 m-0 mt-2">
          Who it is for, and who it is not for.
        </h2>
        <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card>
            <h3 className="pk-h3 m-0">For</h3>
            <p className="pk-body m-0 mt-3 text-muted">
              AI companies moving from flat-rate or per-seat pricing to usage or outcome pricing,
              who suspect some customers cost more to serve than they pay. The usual sign: someone
              on your team already reconciles the monthly model-provider bill against Stripe or
              Chargebee in a spreadsheet.
            </p>
          </Card>
          <Card tone="inset">
            <h3 className="pk-h3 m-0">Not for</h3>
            <ul className="pk-body m-0 mt-3 list-disc space-y-2 pl-5 text-muted marker:text-teal">
              {NOT_FOR.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          </Card>
        </div>
      </Section>

      <Section band="spotlight" labelledBy="cta-h" width="prose" className="text-center">
        <Eyebrow>Next step</Eyebrow>
        <h2 id="cta-h" className="pk-h2 m-0 mt-2">
          Tell us how you price today.
        </h2>
        <p className="pk-body m-0 mx-auto mt-3 max-w-[56ch]">
          A conversation needs no data and no system access.
        </p>
        <div className="mt-6 flex justify-center">
          <Button href="/contact" size="lg">
            Request the audit
          </Button>
        </div>
      </Section>
    </main>
  );
}
