import { Card } from "@/components/ui";

// The six structural pricing bottlenecks, in the founder's words from the
// Consumer Trends tab of the research sheet. Plain statements of how AI
// pricing breaks. No figures: the sheet's numbers are the founder's synthesis
// of operator playbooks and are not evidence for this site.
export const BOTTLENECKS: readonly { id: string; name: string; text: string }[] = [
  {
    id: "cost-floor",
    name: "The cost floor",
    text: "Every query or agentic step has a real, variable cost: model fees, compute and storage. Price too low or bundle it flat, and heavy users push the unit economics negative.",
  },
  {
    id: "packaging",
    name: "The packaging paradox",
    text: "Per-seat pricing penalizes the vendor when the AI replaces headcount. Usage pricing matches your costs, but enterprise finance teams want a bill they can budget.",
  },
  {
    id: "value-metric",
    name: "Value metric and outcome pricing",
    text: "Pricing a completed outcome aligns incentives, but it makes revenue lumpy and hard to forecast, and the outcome is hard to define in a contract. Discounting to win early logos signals low quality.",
  },
  {
    id: "variance",
    name: "Variance and trust",
    text: "Buyers will tolerate a tool that is slower or costs more. They will not tolerate output that is inconsistent, and the human effort that closes the trust gap is a cost too.",
  },
  {
    id: "pilots",
    name: "Pilot revenue versus true ARR",
    text: "Paid pilots can look like recurring revenue and then fail to convert. Humans quietly fixing the work behind the scenes can turn a software business into a services one.",
  },
  {
    id: "bundling",
    name: "Bundling",
    text: "A large incumbent can bundle a single feature into its suite for free. Pricing power comes from owning the whole workflow and your customers' history, not a prompt layer.",
  },
];

export default function Bottlenecks() {
  return (
    <ol className="m-0 grid list-none grid-cols-1 gap-4 p-0 md:grid-cols-2 lg:grid-cols-3">
      {BOTTLENECKS.map((b, i) => (
        <li key={b.id} data-bottleneck={b.id} className="flex">
          <Card className="w-full">
            <span className="pk-small font-semibold tabular-nums text-teal">{String(i + 1).padStart(2, "0")}</span>
            <h3 className="pk-h3 m-0 mt-1">{b.name}</h3>
            <p className="pk-body m-0 mt-2 text-muted">{b.text}</p>
          </Card>
        </li>
      ))}
    </ol>
  );
}
