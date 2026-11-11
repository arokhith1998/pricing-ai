// The six structural pricing bottlenecks, in the founder's words from the
// Consumer Trends tab of the research sheet, one line each. No figures: the
// sheet's numbers are the founder's synthesis and are not evidence for this
// site. /audit reuses the names as its six audit questions.
export const BOTTLENECKS: readonly { id: string; name: string; line: string }[] = [
  {
    id: "cost-floor",
    name: "The cost floor",
    line: "Inference and storage costs are real and variable, so heavy users can push unit economics negative.",
  },
  {
    id: "packaging",
    name: "The packaging paradox",
    line: "Per-seat pricing penalizes the vendor as AI replaces headcount, while buyers want a bill they can budget.",
  },
  {
    id: "value-metric",
    name: "Value metric and outcome pricing",
    line: "Outcome pricing aligns incentives but makes revenue lumpy and hard to define in a contract.",
  },
  {
    id: "variance",
    name: "Variance and trust",
    line: "In B2B and regulated services, inconsistent output is an existential threat.",
  },
  {
    id: "pilots",
    name: "Pilot revenue versus true ARR",
    line: "Paid pilots can look like recurring revenue and then fail to convert.",
  },
  {
    id: "bundling",
    name: "Bundling",
    line: "Large incumbents can bundle a single feature into their suite for free.",
  },
];

export default function Bottlenecks() {
  return (
    <ol className="pk-body m-0 max-w-[72ch] list-none space-y-3 p-0">
      {BOTTLENECKS.map((b) => (
        <li key={b.id} data-bottleneck={b.id}>
          <span className="font-semibold text-fg">{b.name}.</span>{" "}
          <span className="text-muted">{b.line}</span>
        </li>
      ))}
    </ol>
  );
}
