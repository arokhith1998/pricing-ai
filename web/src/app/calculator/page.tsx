import type { Metadata } from "next";
import Link from "next/link";
import LeakageCalculator from "@/components/LeakageCalculator";

export const dynamic = "force-static";

export const metadata: Metadata = {
  title: "Discount leakage calculator · Pricekeel",
  description:
    "Estimate the discount you give back every year, and the slice past a 15% deal-desk line. No signup. The math is shown, and it is the same logic our diagnostic runs on your CSV.",
};

export default function CalculatorPage() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <div className="text-center">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-teal/40 bg-surface px-3 py-1 text-xs font-semibold text-teal">
          <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-teal" />
          Free · no signup · no data leaves your browser
        </span>
        <h1 className="mx-auto mt-4 max-w-2xl text-3xl font-extrabold tracking-tight text-fg sm:text-4xl">
          What is discounting costing you a year?
        </h1>
        <p className="mx-auto mt-3 max-w-2xl text-base text-slate">
          Plug in your booked ACV and average discount. We show the discount you
          give back, and the slice that sits past a typical 15% deal-desk line.
          The math is the same logic our diagnostic runs, applied to round
          numbers. Your real, deal-level figure comes from your CSV.
        </p>
      </div>

      <div className="mt-8">
        <LeakageCalculator />
      </div>

      {/* How the math works — credibility, shown not claimed. --------------- */}
      <section className="mt-12">
        <h2 className="text-lg font-semibold text-fg">How the math works</h2>
        <div className="mt-3 space-y-3 text-sm leading-relaxed text-muted">
          <p>
            <span className="font-medium text-fg">Discount given back</span> is
            list value minus booked value. From your average discount{" "}
            <span className="font-mono text-xs text-fg">d</span>, implied list is{" "}
            <span className="font-mono text-xs text-fg">booked ÷ (1 − d)</span>,
            so the discount given back is{" "}
            <span className="font-mono text-xs text-fg">list − booked</span>.
            This is a description, not a verdict: some of it earns the win.
          </p>
          <p>
            <span className="font-medium text-fg">Above the 15% line</span> is
            the discount given past a common deal-desk policy threshold,{" "}
            <span className="font-mono text-xs text-fg">(d − 15%) × list</span>.
            It is the governance lens. It is correlational, not a refund figure,
            and because it is computed from your average rather than each deal,
            it usually <span className="text-fg">understates</span> the truth.
          </p>
          <p>
            What this calculator deliberately does{" "}
            <span className="text-fg">not</span> do is invent a recovery rate.
            The diagnostic&rsquo;s strongest number, the discount given past the
            point where win rate stops improving, needs your actual won and lost
            deals and a bootstrapped reference discount. That is what the{" "}
            <Link className="text-teal underline" href="/sample">
              real diagnostic
            </Link>{" "}
            produces, deal by deal, with the math logged so a CFO can audit it.
          </p>
        </div>
      </section>
    </main>
  );
}
