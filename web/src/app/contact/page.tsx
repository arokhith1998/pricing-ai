import type { Metadata } from "next";
import Link from "next/link";
import Reveal from "@/components/Reveal";

export const dynamic = "force-static";
export const metadata: Metadata = {
  title: "Contact · Pricekeel",
  description:
    "Reach Adhithya at Pricekeel. Email, LinkedIn, or the lead form for a free diagnostic.",
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
          Talk to the founder, not a contact form.
        </h1>
        <p className="mt-3 max-w-2xl text-muted">
          Pricekeel is in design-partner mode. Every conversation goes
          straight to Adhithya. Pick whichever channel is easiest.
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
              The fastest path. NDA on request. I reply within one business day.
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
              Good for warm intros and quick context-sharing without an inbox.
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
              A worked example on a 2,000-deal synthetic book. Two minutes to
              skim before you write.
            </p>
          </Link>
        </section>
      </Reveal>

      <Reveal delay={0.05}>
        <section className="mt-12 rounded-xl border border-mist bg-surface p-6">
          <h2 className="text-lg font-semibold text-fg">
            What an intro email could say
          </h2>
          <p className="mt-1 text-sm text-muted">
            Optional template if a blank cursor is the only thing in the way.
          </p>
          <pre className="mt-4 overflow-x-auto rounded-lg border border-mist bg-surface-2 p-4 text-xs leading-relaxed text-ink">
{`Subject: Pricekeel diagnostic, [Your company]

Hi Adhithya,

I'm [name], [title] at [company] ($XM ARR, [usage-based / hybrid / seats]).
Saw your write-up on discount leakage and want to see the methodology run
on our own deal book.

We can send a CSV of the last [N] quarters of closed opportunities (won
and lost). Happy to sign an NDA first.

What's the next step?
`}
          </pre>
        </section>
      </Reveal>

      <Reveal delay={0.05}>
        <section className="mt-8 rounded-xl border border-mist bg-surface p-6">
          <h2 className="text-lg font-semibold text-fg">
            Three things worth knowing before you write
          </h2>
          <ul className="mt-3 space-y-2 text-sm text-muted">
            <li>
              <span className="font-medium text-fg">First diagnostic is free.</span>{" "}
              For design partners, including a 30-minute readout call.
            </li>
            <li>
              <span className="font-medium text-fg">Your CSV is processed in memory.</span>{" "}
              Never written to disk on our servers, never sent to a cloud LLM.
              Aggregates and column names only. Full details on{" "}
              <Link href="/trust" className="text-teal underline">
                /trust
              </Link>
              .
            </li>
            <li>
              <span className="font-medium text-fg">We are at pre-seed.</span>{" "}
              Three design partners in the cohort, $5K/month managed cadence
              for months two through six. Off-ramp at any time.
            </li>
          </ul>
        </section>
      </Reveal>

      <Reveal delay={0.05}>
        <section className="mt-8 text-center text-sm text-muted">
          <p>
            Prefer the founder show? See the{" "}
            <Link href="/" className="text-teal underline">
              landing page
            </Link>{" "}
            for the bio and credibility chips.
          </p>
        </section>
      </Reveal>
    </main>
  );
}
