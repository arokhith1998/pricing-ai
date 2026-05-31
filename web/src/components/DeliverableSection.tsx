// Landing-page section answering the reviewer's gap: "very clear 'what you
// get after the diagnostic' section". Four concrete deliverables the
// prospect walks away with after a free diagnostic engagement. Each is
// real and pointable-to in the live product.

const ITEMS: { title: string; body: string }[] = [
  {
    title: "Executive summary",
    body:
      "A one-page written narrative your CFO can read in two minutes: booked value, price realization, win point, the headline upside, the top three deals to investigate. Plain English, no jargon.",
  },
  {
    title: "Win-curve report",
    body:
      "Win rate by discount band with the calculated reference point (the band where bigger discounts stop buying wins). The chart your Head of Pricing forwards to the CRO.",
  },
  {
    title: "Per-deal guidance",
    body:
      "For each open opportunity you send: recommended discount, expected-value lift, win-probability change, and the top three factors the model thinks drive the deal. Decision support for the deal-desk call.",
  },
  {
    title: "Defended-vs-investigate list",
    body:
      "Won deals split into 'discount earned the win' (defend in sales review) vs 'discount worth a retrospective look' (route to deal-desk debrief). Sales-friendly framing of the same data.",
  },
];

export default function DeliverableSection() {
  return (
    <section aria-label="What you get from the diagnostic">
      <div className="text-center">
        <p className="text-xs font-semibold uppercase tracking-wider text-teal">
          What you walk away with
        </p>
        <h2 className="mt-2 text-xl font-bold text-fg sm:text-2xl">
          The diagnostic is four artifacts, not a dashboard you have to interpret
        </h2>
        <p className="mx-auto mt-2 max-w-2xl text-sm text-muted">
          Each one is built so a Head of Pricing can forward it to the CFO
          unchanged. No screenshots-of-screenshots, no copy-paste cleanup.
        </p>
      </div>
      <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-2">
        {ITEMS.map((it, i) => (
          <div
            key={it.title}
            className="rounded-xl border border-mist bg-surface p-5"
          >
            <div className="flex items-baseline gap-2">
              <span className="text-xs font-bold tabular-nums text-teal">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div className="text-base font-semibold text-fg">{it.title}</div>
            </div>
            <p className="mt-1 text-sm text-muted">{it.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
