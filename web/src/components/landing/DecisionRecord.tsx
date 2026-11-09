import { Artifact, StatusIcons, StatusPill, SyntheticTag } from "@/components/ui";
import CountUp from "@/components/CountUp";
import { HERO_EXCESS, RECORD, SYNTHETIC_DEAL_TAG } from "@/lib/landing-sample";
import { ciText, Field, money, pct } from "./parts";

// The hero artifact: one deal from the bundled synthetic sample, rendered with
// the fields the product records. Opportunity id and segment, never the
// account name. Static server markup, no animation, nothing to hydrate beyond
// the count-up of the one headline number.
export default function DecisionRecord() {
  const r = RECORD;
  return (
    <Artifact label="Decision record for one synthetic sample deal" caption={SYNTHETIC_DEAL_TAG}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="pk-eyebrow m-0">Decision record</p>
          <p className="pk-mono m-0 mt-1 text-fg">
            {r.opportunityId} <span className="text-muted">· {r.segment}</span>
          </p>
        </div>
        <SyntheticTag />
      </div>

      <div className="mt-4 rounded-card border border-border bg-surface-2 p-4">
        <StatusPill tone="leak" label="Gap to segment win point" icon={StatusIcons.leak} />
        <p className="pk-figure m-0 mt-2 text-coral">
          <CountUp to={HERO_EXCESS} format="moneyShort" />
        </p>
        <p className="pk-small m-0 mt-1 text-muted">
          booked above each segment&rsquo;s win point, in a synthetic 2,000-deal book
        </p>
      </div>

      <dl className="m-0 mt-4 grid grid-cols-2 gap-x-4 gap-y-3">
        <Field label="Requested discount" note={`on ${money(r.listAcv)} list`}>
          {pct(r.requestedDiscount)}
        </Field>
        <Field label="Segment reference band" note={`${r.segment}, ${r.referenceBasis}`}>
          {r.referenceBandLabel}
        </Field>
        <Field label={`Win rate, ${r.requestedBand.label} band`} note={`interval ${ciText(r.requestedBand)}`}>
          {pct(r.requestedBand.winRate)}
        </Field>
        <Field label={`Win rate, ${r.referenceBandLabel} band`} note={`interval ${ciText(r.referenceBand)}`}>
          {pct(r.referenceBand.winRate)}
        </Field>
        <Field label="Method">{r.method}</Field>
        <Field label="evidence_version" mono>
          {r.evidenceVersion}
        </Field>
      </dl>

      <p className="pk-small m-0 mt-4 border-t border-border pt-3 text-muted">
        <span className="font-semibold text-fg">Decision log:</span> a person chooses accept, trade
        or override. The record keeps the requested terms and this evidence.
      </p>
    </Artifact>
  );
}
