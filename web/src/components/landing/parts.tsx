import type { ReactNode } from "react";
import { money, pct } from "@/lib/format";
import type { ProbeBand } from "@/lib/landing-sample";

// "42.3% (36.0% to 48.6%)": a win rate with its confidence interval.
export function ciText(b: ProbeBand): string {
  return `${pct(b.ciLow)} to ${pct(b.ciHigh)}`;
}

export { money, pct };

// One labelled value in a record. dt/dd so assistive tech reads label then value.
export function Field({
  label,
  children,
  note,
  mono = false,
}: {
  label: string;
  children: ReactNode;
  note?: ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="min-w-0">
      <dt className="pk-small text-muted">{label}</dt>
      <dd className="m-0 mt-0.5">
        <span className={`font-semibold tabular-nums text-fg ${mono ? "pk-mono break-all" : "text-body"}`}>
          {children}
        </span>
        {note ? <span className="pk-small block text-muted">{note}</span> : null}
      </dd>
    </div>
  );
}

// A band's win rate as a bar with its confidence interval whisker. Decorative
// geometry only: the numbers are always printed beside it.
export function WinBar({ band, emphasis }: { band: ProbeBand; emphasis?: boolean }) {
  const left = `${(band.ciLow * 100).toFixed(1)}%`;
  const width = `${((band.ciHigh - band.ciLow) * 100).toFixed(1)}%`;
  return (
    <div className="relative h-3 w-full rounded-full bg-surface-2" aria-hidden>
      <div
        className={`absolute inset-y-0 left-0 rounded-full ${emphasis ? "bg-teal" : "bg-muted/60"}`}
        style={{ width: `${(band.winRate * 100).toFixed(1)}%` }}
      />
      <div
        className="absolute top-1/2 h-0.5 -translate-y-1/2 bg-fg"
        style={{ left, width }}
      />
    </div>
  );
}
