import type { ReactNode } from "react";
import { cx } from "./cx";
import SyntheticTag, { type SyntheticVariant } from "./SyntheticTag";

// A KPI. Every Stat declares where its figure comes from:
//  - source "sample": the figure is from the bundled synthetic sample. The
//    Stat renders the SyntheticTag itself, so a sample figure cannot appear
//    without its label. `syntheticVariant` may switch it to "illustrative".
//  - source "input": the figure is computed from numbers the reader typed.
// Omitting `source` is a type error.
type StatBase = {
  label: string;
  value: ReactNode;
  note?: ReactNode;
  className?: string;
};

export type StatProps =
  | (StatBase & { source: "sample"; syntheticVariant?: SyntheticVariant })
  | (StatBase & { source: "input"; syntheticVariant?: never });

export default function Stat(props: StatProps) {
  const { label, value, note, className } = props;
  return (
    <div data-stat-source={props.source} className={cx("min-w-0", className)}>
      <dl className="m-0">
        <dt className="pk-small text-muted">{label}</dt>
        <dd className="pk-figure m-0 mt-1">{value}</dd>
      </dl>
      {note ? <p className="pk-small mt-1 text-muted">{note}</p> : null}
      {props.source === "sample" ? (
        <SyntheticTag variant={props.syntheticVariant ?? "sample"} className="mt-2" />
      ) : null}
    </div>
  );
}
