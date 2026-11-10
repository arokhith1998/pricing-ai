import { cx } from "./cx";

export const SYNTHETIC_LABELS = {
  sample: "Synthetic sample",
  illustrative: "Illustrative, not customer data",
} as const;

export type SyntheticVariant = keyof typeof SYNTHETIC_LABELS;

// The provenance label for any figure that comes from the bundled synthetic
// 2,000-deal sample ("sample") or from a hand-built example ("illustrative").
// Neutral tone on purpose: provenance is not a status, so it never uses coral,
// green or amber. The text is fixed here so no page hand-types a variant of it.
export default function SyntheticTag({
  variant = "sample",
  className,
}: {
  variant?: SyntheticVariant;
  className?: string;
}) {
  return (
    <span
      data-synthetic-tag={variant}
      className={cx(
        "pk-micro inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border border-control px-2 py-0.5 text-muted",
        className,
      )}
    >
      <svg aria-hidden width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="1" y="1" width="8" height="8" rx="1.5" strokeDasharray="2 1.5" />
      </svg>
      {SYNTHETIC_LABELS[variant]}
    </span>
  );
}
