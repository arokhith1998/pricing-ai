import type { Metadata } from "next";
import Link from "next/link";
import Reveal from "@/components/Reveal";

export const dynamic = "force-static";
export const metadata: Metadata = {
  title: "Contact · Pricekeel",
  description:
    "Request a Pricekeel Salesforce design-partner walkthrough with the founder.",
};

const EMAIL = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "adhithya@pricekeel.com";
const LINKEDIN =
  process.env.NEXT_PUBLIC_FOUNDER_LINKEDIN ??
  "https://www.linkedin.com/in/adhithyarokhith/";

export default function ContactPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Reveal>
        <p className="text-sm font-semibold uppercase tracking-wider text-teal">
          Contact
        </p>
        <h1 className="mt-2 text-3xl font-bold text-fg sm:text-4xl">
          Bring one real discount exception.
        </h1>
        <p className="mt-3 max-w-2xl text-muted">
          Pricekeel is in design-partner mode for $20–100M ARR B2B SaaS teams
          running Salesforce. Every request goes directly to Adhithya. The
          first walkthrough uses a redacted or hypothetical deal, no credentials required.
        </p>
      </Reveal>

      <Reveal delay={0.05}>
        <section className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-3">
          <a
            href={`mailto:${EMAIL}?subject=Pricekeel%20intro`}
            className="group rounded-xl border border-mist bg-surface p-5 transition hover:-translate-y-0.5 hover:border-teal hover:shadow-md"
          >
            <div className="text-xs font-semibold uppercase tracking-wider text-teal">
              Email
            </div>
            <div className="mt-1 text-base font-semibold text-fg group-hover:text-teal">
              {EMAIL}
            </div>
            <p className="mt-1 text-sm text-muted">
              The fastest path. NDA on request. Expect a reply within one business day.
            </p>
          </a>
          <a
            href={LINKEDIN}
            target="_blank"
            rel="noreferrer noopener"
            className="group rounded-xl border border-mist bg-surface p-5 transition hover:-translate-y-0.5 hover:border-teal hover:shadow-md"
          >
            <div className="text-xs font-semibold uppercase tracking-wider text-teal">
              LinkedIn
            </div>
            <div className="mt-1 text-base font-semibold text-fg group-hover:text-teal">
              DM Adhithya
            </div>
            <p className="mt-1 text-sm text-muted">
              Good for warm introductions and a short note on your pricing workflow.
            </p>
          </a>
          <Link
            href="/sample"
            className="group rounded-xl border border-teal/40 bg-surface p-5 transition hover:-translate-y-0.5 hover:border-teal hover:shadow-md"
          >
            <div className="text-xs font-semibold uppercase tracking-wider text-teal">
              See the product first
            </div>
            <div className="mt-1 text-base font-semibold text-fg group-hover:text-teal">
              Open the sample diagnostic
            </div>
            <p className="mt-1 text-sm text-muted">
              A worked example on 2,000 synthetic closed deals. Two minutes to
              see the evidence layer before you write.
            </p>
          </Link>
        </section>
      </Reveal>

      <Reveal delay={0.05}>
        <section className="mt-12 rounded-xl border border-mist bg-surface p-6">
          <h2 className="text-lg font-semibold text-fg">
            A useful first email
          </h2>
          <p className="mt-1 text-sm text-muted">
            Optional template if a blank cursor is the only thing in the way.
          </p>
          <pre className="mt-4 overflow-x-auto rounded-lg border border-mist bg-surface-2 p-4 text-xs leading-relaxed text-ink">
{`Subject: Pricekeel Salesforce pilot, [Your company]

Hi Adhithya,

I'm [name], [title] at [company] ($XM ARR, [usage-based / hybrid]).
We use Salesforce and want to improve how [Deal Desk / RevOps / Pricing]
handles discount exceptions.

A representative deal is about $[ACV], and our current approval flow is
[one sentence]. The question we want Pricekeel to answer is [question].

Can we walk through that deal before discussing a connection?
`}
          </pre>
        </section>
      </Reveal>

      <Reveal delay={0.05}>
        <section className="mt-8 rounded-xl border border-mist bg-surface p-6">
          <h2 className="text-lg font-semibold text-fg">
            What happens next
          </h2>
          <ul className="mt-3 space-y-2 text-sm text-muted">
            <li>
              <span className="font-medium text-fg">Start without credentials.</span>{" "}
              The first conversation uses one redacted or hypothetical pricing
              exception to test the workflow and recommendation logic.
            </li>
            <li>
              <span className="font-medium text-fg">Connect only after the workflow fits.</span>{" "}
              Salesforce OAuth tokens stay server-side and encrypted at rest.
              Opportunity rows are not sent to a cloud LLM. Full details on{" "}
              <Link href="/trust" className="text-teal underline">
                /trust
              </Link>
              .
            </li>
            <li>
              <span className="font-medium text-fg">Scope follows evidence.</span>{" "}
              If the workflow is useful, we agree on field mapping, success
              metrics, security review, and a founder-led pilot. Commercial
              structure is shared after that scoping conversation.
            </li>
          </ul>
        </section>
      </Reveal>

      <Reveal delay={0.05}>
        <section className="mt-8 text-center text-sm text-muted">
          <p>Already have a customer access code? <Link href="/crm" className="text-teal underline">Open the Salesforce workspace</Link>.</p>
        </section>
      </Reveal>
    </main>
  );
}
