import type { ElementType, ReactNode } from "react";
import { cx } from "./cx";

// Card (content block) and inset (a well inside a card, table heads). One
// radius family, a hairline that is decorative only. `interactive` adds the
// 120ms teal border hover; there is no tilt or lift anywhere.
export default function Card({
  as: Tag = "div",
  tone = "card",
  interactive = false,
  className,
  children,
}: {
  as?: ElementType;
  tone?: "card" | "inset";
  interactive?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Tag
      className={cx(
        tone === "inset" ? "pk-surface-inset" : "pk-surface-card",
        interactive && "pk-surface-interactive",
        "p-5 sm:p-6",
        className,
      )}
    >
      {children}
    </Tag>
  );
}
