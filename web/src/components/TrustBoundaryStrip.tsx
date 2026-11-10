// Section 4 of the landing page: the engine's boundaries, stated once, as a
// two-column "will / will not" list, then methodology, founder credential and
// trust links in one compact row.
import Link from "next/link";
import { Card } from "@/components/ui";

const METHOD_AUTHORS = ["Nagle", "Ramanujam", "Bertini", "Simon-Kucher", "Rivera"];

const WILL = [
  "Say whether each recommendation is a modeled optimum or a support floor.",
  "Say insufficient data instead of a number when the book is too thin.",
  "Keep the terms as requested and record the human decision with its evidence.",
];

const WILL_NOT = [
  "Set or approve a price. A person decides.",
  "Relabel a CRM cost figure. It stays a cost proxy, never labeled margin.",
  "Score commit, ramp or overage yet. V1 governs the discount on committed ACV; those are captured, not scored.",
  "Keep row-level deal data. It is processed in memory and deleted.",
];

function Column({ title, items, mark }: { title: string; items: string[]; mark: string }) {
  return (
    <Card>
      <h3 className="pk-h3 m-0">{title}</h3>
      <ul className="m-0 mt-4 list-none space-y-3 p-0">
        {items.map((t) => (
          <li key={t} className="pk-body m-0 flex gap-3 text-fg">
            <span aria-hidden className="pk-mono mt-0.5 text-teal">
              {mark}
            </span>
            <span>{t}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export default function TrustBoundaryStrip() {
  return (
    <div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Column title="The engine will" items={WILL} mark="+" />
        <Column title="The engine will not" items={WILL_NOT} mark="-" />
      </div>
      <div className="pk-small mt-6 flex flex-wrap items-center gap-x-4 gap-y-2 text-muted">
        <span>Method: {METHOD_AUTHORS.join(" · ")}.</span>
        <span>Built by Adhithya Bhaskar, Simon Business School.</span>
        <Link href="/trust" className="inline-flex min-h-11 items-center font-medium text-teal hover:underline">
          Trust
        </Link>
        <Link href="/methodology" className="inline-flex min-h-11 items-center font-medium text-teal hover:underline">
          Methodology
        </Link>
      </div>
    </div>
  );
}
