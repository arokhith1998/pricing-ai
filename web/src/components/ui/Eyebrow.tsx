import type { ReactNode } from "react";
import { cx } from "./cx";

// Uppercase section label, teal (10.29:1 on canvas). Carries no status meaning.
export default function Eyebrow({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <p className={cx("pk-eyebrow", className)}>{children}</p>;
}
