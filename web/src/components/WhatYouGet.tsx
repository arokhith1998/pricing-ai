import { Card, Eyebrow } from "@/components/ui";
import { RECORD } from "@/lib/landing-sample";
import { ciText, pct } from "@/components/landing/parts";

// One record, three views: the same synthetic deal rendered for the three
// readers. The role lines are unchanged from the earlier landing page; the
// excerpt under each is read from the same record the hero shows.
const r = RECORD;

const ROLES: { role: string; line: string; excerpt: string }[] = [
  {
    role: "Deal Desk",
    line: "See the guardrail and the closest comparable deals. Accept or override.",
    excerpt: `${r.opportunityId}: ${pct(r.requestedDiscount)} requested against a ${r.referenceBandLabel} reference band.`,
  },
  {
    role: "Pricing",
    line: "See realization and win rate by segment and band, with cited competitor context.",
    excerpt: `${r.requestedBand.label} band wins ${pct(r.requestedBand.winRate)} (interval ${ciText(r.requestedBand)}).`,
  },
  {
    role: "Finance",
    line: "See who approved what, and where CRM discount data stops. CRM cost figures are a cost proxy, not margin; margin needs billing or ERP.",
    excerpt: `The record keeps the requested terms, this evidence and who decided.`,
  },
];

export default function WhatYouGet() {
  return (
    <ul className="m-0 grid list-none grid-cols-1 gap-4 p-0 md:grid-cols-3">
      {ROLES.map((item) => (
        <li key={item.role} className="flex">
          <Card className="flex w-full flex-col">
            <Eyebrow>{item.role}</Eyebrow>
            <p className="pk-body m-0 mt-3">{item.line}</p>
            <p className="pk-small pk-mono m-0 mt-auto border-t border-border pt-3 text-muted">
              {item.excerpt}
            </p>
          </Card>
        </li>
      ))}
    </ul>
  );
}
