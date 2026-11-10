import { Artifact, StatusIcons, StatusPill, SyntheticTag } from "@/components/ui";
import { moneyShort } from "@/lib/format";
import { RECORD, SYNTHETIC_DEAL_TAG } from "@/lib/landing-sample";
import { ciText, Field, money, pct } from "./parts";

// The hero artifact: one deal from the bundled synthetic sample, rendered with
// the fields the product records. Opportunity id and segment, never the
// account name. Static server markup: no animation and no client work, so the
// number is correct with JavaScript off (a count-up would show $0 there).
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

      <div className="mt-3 rounded-card border border-border bg-surface-2 p-3">
        <StatusPill tone="leak" label="This deal's gap to its win point" icon={StatusIcons.leak} />
        <p className="pk-figure m-0 mt-2 text-coral">{moneyShort(r.excessDollars)}</p>
        <p className="pk-small m-0 mt-1 text-muted">
          discount given beyond the {r.segment} win point on this one synthetic deal
        </p>
      </div>

      <dl className="m-0 mt-3 grid grid-cols-2 gap-x-4 gap-y-2">
        <Field label="Requested discount" note={`on ${money(r.listAcv)} list`}>
          {pct(r.requestedDiscount)}
        </Field>
        <Field label="Segment reference band" note={`${r.segment}, ${r.referenceBasis}`}>
          {r.referenceBandLabel}
        </Field>
        <Field label={`Win rate, ${r.requestedBand.label} band, all segments`} note={`interval ${ciText(r.requestedBand)}`}>
          {pct(r.requestedBand.winRate)}
        </Field>
        <Field label={`Win rate, ${r.referenceBandLabel} band, all segments`} note={`interval ${ciText(r.referenceBand)}`}>
          {pct(r.referenceBand.winRate)}
        </Field>
        <Field label="Method">{r.method}</Field>
        <Field label="Sample ID, this page only, not an audit hash" mono>
          {r.pageFingerprint}
        </Field>
      </dl>

      <p className="pk-small m-0 mt-3 border-t border-border pt-3 text-muted">
        <span className="font-semibold text-fg">Decision log:</span> a person chooses accept or
        override. The record keeps the requested terms and this evidence.
      </p>
    </Artifact>
  );
}
