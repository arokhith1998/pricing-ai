import type { Metadata } from "next";
import Link from "next/link";
import { CTA } from "@content/landing";

export const metadata: Metadata = {
  title: "Manifesto · Pricekeel",
  description:
    "Discounting is the most expensive habit in B2B SaaS and the least measured. Pricekeel exists to turn it into a number you can see.",
};

export const dynamic = "force-static";

export default function ManifestoPage() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-20 sm:py-28">
      <p className="text-sm font-medium uppercase tracking-wider text-teal">Manifesto</p>
      <h1 className="mt-3 text-balance font-extrabold leading-[1.1] tracking-tight text-fg text-[clamp(2.25rem,5vw,3.5rem)]">
        Discounting is the most expensive habit in B2B SaaS, and the least measured.
      </h1>

      <div className="mt-10 space-y-6 text-lg leading-relaxed text-muted">
        <p>
          Every quarter, deals close. Someone gives up price to close them. And
          almost no one goes back to ask the only question that matters: did that
          discount actually buy the win, or did the deal close anyway?
        </p>
        <p>
          We think most discount is not strategy. It is reflex. The reflex of a
          rep against a deadline, a quarter-end forecast, a competitor in the
          room. Reflexes are not bad. Unmeasured reflexes are.
        </p>
        <p>
          <span className="font-semibold text-fg">The cure is not a new rule. It is a number you can see.</span>{" "}
          Your own closed deals already contain it. Plot win rate against discount
          and the curve bends, then flattens. Past the point where it flattens,
          extra discount bought no extra wins. That is not leakage you assume. It
          is leakage you can point at, deal by deal.
        </p>
        <p>
          So that is what we built. You send one CSV of your last four quarters.
          We find your win point, the dollars given past it, the segments where
          price quietly erodes, and the quarter-end tax you pay every three
          months. Then we show you the deals behind every number, the comparable
          wins and losses, the reasoning. Not a black box. A worked answer.
        </p>
        <p>
          We will tell you what this is not. It is correlational, not causal.
          Bigger and harder deals attract bigger discounts, so some of the gap is
          earned. We will never hand you a refund figure dressed up as certainty.
          Explainability over accuracy. A human makes the call. Every time.
        </p>
        <p>
          This is for the teams the enterprise pricing suites quote six figures to
          ignore. The deal desks running on spreadsheets. The pricing and RevOps
          people at Series B to C usage-based companies who know the leak is real
          and have never been able to put a number on it.
        </p>
        <p className="font-semibold text-fg">
          Stop giving away price that wins you nothing. Start by seeing how much
          you already do.
        </p>
      </div>

      <div className="mt-12">
        <Link
          href={CTA.href}
          className="inline-flex items-center justify-center rounded-full bg-teal px-7 py-3.5 text-base font-semibold text-bg transition hover:brightness-110"
        >
          {CTA.label}
        </Link>
      </div>
    </main>
  );
}
