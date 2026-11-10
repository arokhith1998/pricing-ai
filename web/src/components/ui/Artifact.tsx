import type { ReactNode } from "react";
import { cx } from "./cx";

// The artifact surface: the decision record and readout renders. One per
// page (the glow is the emphasis). `label` is the accessible name and is
// required. Anything numeric inside should carry a SyntheticTag.
export default function Artifact({
  label,
  caption,
  className,
  children,
}: {
  label: string;
  caption?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <figure aria-label={label} className="m-0">
      <div className={cx("pk-surface-artifact p-5 sm:p-6", className)}>{children}</div>
      {caption ? (
        <figcaption className="pk-small mt-3 text-muted">{caption}</figcaption>
      ) : null}
    </figure>
  );
}
