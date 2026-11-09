import type { ReactNode } from "react";
import Eyebrow from "./Eyebrow";
import { cx } from "./cx";

// The one h1 of a page: optional eyebrow, the title, an optional lead
// paragraph (measure capped at 68ch), optional actions. Pages render exactly
// one PageHeader.
export default function PageHeader({
  title,
  eyebrow,
  lead,
  actions,
  className,
}: {
  title: ReactNode;
  eyebrow?: ReactNode;
  lead?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <header className={cx("flex flex-col gap-3", className)}>
      {eyebrow ? <Eyebrow>{eyebrow}</Eyebrow> : null}
      <h1 className="pk-h1 text-balance">{title}</h1>
      {lead ? <p className="pk-lead mt-1">{lead}</p> : null}
      {actions ? <div className="mt-3 flex flex-wrap items-center gap-3">{actions}</div> : null}
    </header>
  );
}
