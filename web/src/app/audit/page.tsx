import { Button, Eyebrow, PageHeader, Section } from "@/components/ui";
import { pageMetadata } from "@/lib/page-metadata";
import { AUDIT_DAYS, AUDIT_DELIVERY_GUARANTEE, AUDIT_FOLLOW_ON, AUDIT_PRICE, COST_BASIS_LABEL } from "@/lib/audit-offer";
import { BOOKING_LABEL, BOOKING_URL } from "@/lib/site-nav";

// PK-116 (F17): the offer on one short page. Under 350 words, in this order:
// what you get, how it works, what we need, price, who it is for, one line on
// readiness, one button. A test pins the word count and the section order.
export const dynamic = "force-static";
export const metadata = pageMetadata({
  title: "14-day pricing audit",
  description:
    "A done-for-you 14-day pricing audit for AI companies: which customers and plans cost more to serve than they pay, and a packaging fix to decide on.",
  path: "/audit",
});

const GET: string[] = [
  `Each customer and plan with its ${COST_BASIS_LABEL}.`,
  "The usage level where each plan stops covering its cost.",
  "One recommended packaging structure and two alternatives, for you to decide.",
  "A 60-minute readout and a PDF your finance lead can forward.",
];

const STEPS: { title: string; body: string }[] = [
  {
    title: "Talk to us.",
    body: "A 20-minute call about how you price today. No data, no access.",
  },
  {
    title: "Sign, then send exports.",
    body: "After a mutual NDA and data addendum, you send billing and cost exports with customers replaced by codes.",
  },
  {
    title: `Get the readout in ${AUDIT_DAYS} days.`,
    body: "The days count from the day your files arrive and check out.",
  },
];

const NEED: string[] = [
  "Billing exports",
  "Model-provider and cloud cost exports",
  "A customer list with plan and start date",
  "One person who owns pricing",
];

export default function AuditPage() {
  return (
    <main id="main" tabIndex={-1} className="outline-none">
      <Section>
        <PageHeader title="Find which customers cost you more than they pay." />
      </Section>

      <Section band="band" labelledBy="get-h">
        <Eyebrow>What you get</Eyebrow>
        <h2 id="get-h" className="pk-h2 m-0 mt-2">
          A {AUDIT_DAYS}-day, done-for-you audit of your billing and cost exports.
        </h2>
        <ul className="pk-body mt-6 max-w-prose list-disc space-y-2 pl-5 text-muted marker:text-teal">
          {GET.map((g) => (
            <li key={g}>{g}</li>
          ))}
        </ul>
      </Section>

      <Section labelledBy="how-h">
        <Eyebrow>How it works</Eyebrow>
        <h2 id="how-h" className="pk-h2 m-0 mt-2">
          Three steps.
        </h2>
        <ol className="pk-body mt-6 max-w-prose list-decimal space-y-3 pl-6 text-muted marker:text-teal">
          {STEPS.map((s) => (
            <li key={s.title}>
              <span className="font-medium text-fg">{s.title}</span> {s.body}
            </li>
          ))}
        </ol>
      </Section>

      <Section band="band" labelledBy="need-h">
        <Eyebrow>What we need</Eyebrow>
        <h2 id="need-h" className="pk-h2 m-0 mt-2">
          Exports, not access.
        </h2>
        <ul className="pk-body mt-6 max-w-prose list-disc space-y-2 pl-5 text-muted marker:text-teal">
          {NEED.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
        <p className="pk-body mt-4 max-w-prose text-muted">No API keys, no prompts, no end-user data.</p>
      </Section>

      <Section labelledBy="price-h">
        <Eyebrow>Price</Eyebrow>
        <h2 id="price-h" className="pk-h2 m-0 mt-2">
          {AUDIT_PRICE} fixed, paid upfront.
        </h2>
        <p className="pk-body mt-3 max-w-prose font-medium text-fg" data-testid="delivery-guarantee">
          {AUDIT_DELIVERY_GUARANTEE}
        </p>
        <p className="pk-body mt-2 max-w-prose text-muted">
          We recommend, you decide; we do not promise recovered revenue.
        </p>
        <p className="pk-body mt-2 max-w-prose text-muted" data-testid="follow-on">
          {AUDIT_FOLLOW_ON}
        </p>
      </Section>

      <Section band="band" labelledBy="who-h">
        <Eyebrow>Who it is for</Eyebrow>
        <h2 id="who-h" className="pk-h2 m-0 mt-2">
          AI and B2B software companies changing how they price.
        </h2>
        <p className="pk-body mt-3 max-w-prose text-muted">
          Companies moving from flat or per-seat pricing to usage or outcome pricing, with at least 10
          billed customers and 3 months of billing history.
        </p>
      </Section>

      <Section band="spotlight" width="prose" className="text-center">
        <p className="pk-body m-0 mx-auto max-w-[56ch]" data-testid="readiness">
          We take no files until the paperwork is signed; a conversation needs none.
        </p>
        <div className="mt-6 flex justify-center">
          <Button href={BOOKING_URL} size="lg">
            {BOOKING_LABEL}
          </Button>
        </div>
      </Section>
    </main>
  );
}
