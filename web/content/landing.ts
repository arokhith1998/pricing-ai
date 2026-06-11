// Single source of truth for the landing copy and the ONE call-to-action.
//
// Discipline (aqqrue.com flow benchmark, June 2026): one idea per viewport,
// one CTA repeated verbatim, outcome numbers not adjectives. We emulate the
// STRUCTURE only — all copy here is our own (IP-cautious policy, see
// vault/Decisions/2026-05-30-legal-compliance-audit.md).
//
// The numbers in `outcomes` are the real demo-sample figures from
// pricing.diagnostic.run on data/synthetic/deals.csv (2,000 deals), not
// invented. No em dashes anywhere (house style).

export const CTA = { label: "Get your leakage number", href: "/sample" } as const;

// Founding-cohort scarcity. True number only, no urgency theater.
export const SLOTS = 10;

export const announcement =
  `Founding cohort: ${SLOTS} free diagnostic slots for usage-based SaaS.`;

export const hero = {
  headline: "Stop giving away price that wins you nothing.",
  subhead:
    "A free, NDA-backed diagnostic on your last four quarters of closed deals. " +
    "One CSV in, your leakage number out.",
};

// Four use-case cards. Capability name + two concrete sentences in the
// customer's own vocabulary. Each card gets one short scroll-triggered motion.
export const useCases: { name: string; body: string }[] = [
  {
    name: "Find the leak",
    body: "Price realization by segment. See where booked divided by list quietly fell to 0.81.",
  },
  {
    name: "Win rate by discount band",
    body: "The curve that shows the point where discounting stopped buying you wins.",
  },
  {
    name: "Quarter-end effect",
    body: "What the last week of the quarter actually costs you, in dollars, every quarter.",
  },
  {
    name: "Deals to investigate",
    body: "A ranked list with the why attached: the comparable deals, not a black box.",
  },
];

export const midCta = "Your own number, on your own deals. Not a generic benchmark.";

export const proof = {
  title: "Explore a full diagnostic.",
  subtitle: "Synthetic data, real math. The same analysis we run on your CSV, on 2,000 sample deals.",
};

// Three steps. The data ask is deliberately small: one CSV, no integration.
export const howItWorks: { step: string; title: string; body: string }[] = [
  {
    step: "01",
    title: "Sign the one-page mutual NDA",
    body: "Mutual, plain-language, one page. Your deal data is yours and stays yours.",
  },
  {
    step: "02",
    title: "Export one CSV",
    body: "About 30 minutes, no integration. The schema doc lists the ten columns we need.",
  },
  {
    step: "03",
    title: "Get the readout in days",
    body: "Every number is explainable back to the deals behind it. No black box.",
  },
];

// Outcome numbers from the real sample, honestly labeled. One row, three max.
export const outcomes = {
  caption: "From 2,000 synthetic deals, run through the live diagnostic:",
  stats: [
    { value: "$11.2M", label: "given past the win point, worth investigating" },
    { value: "81.4%", label: "blended price realization (booked over list)" },
    { value: "16.7%", label: "of booked value sat beyond the reference discount" },
  ],
};

export const trust: { title: string; body: string }[] = [
  {
    title: "Mutual NDA, standard",
    body: "We sign yours or send ours before any data changes hands.",
  },
  {
    title: "Your data never trains a model",
    body: "Row-level deal data is processed to produce your result, then deleted. It is never used to train anything.",
  },
  {
    title: "Deletion on request",
    body: "Uploaded files are processed in memory and not retained. Ask and we delete everything on file.",
  },
  {
    title: "Correlational, not causal",
    body: "Excess discount is a prioritized list to investigate, not a refund figure. We say so, on every readout.",
  },
];

export const close = {
  title: "For the deal desks running on spreadsheets.",
  body:
    "Pricing and RevOps teams at Series B to C, usage-based SaaS, the ones the " +
    "enterprise pricing suites quote six figures to ignore. If that is you, " +
    "there is a slot.",
};
