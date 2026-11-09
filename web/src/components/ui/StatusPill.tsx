import type { ReactNode } from "react";
import { cx } from "./cx";

export type StatusTone = "leak" | "ok" | "flag" | "info";

// Status color carries meaning only: coral is leakage or a gap, green is
// realization or within policy, amber is a governance flag or pending, teal is
// neutral information. Color is never the only signal, so `label` and `icon`
// are both required.
const TONES: Record<StatusTone, string> = {
  leak: "border-coral/40 bg-coral/10 text-coral",
  ok: "border-green/40 bg-green/10 text-green",
  flag: "border-amber/40 bg-amber/10 text-amber",
  info: "border-teal/40 bg-teal/10 text-teal",
};

const svgProps = {
  "aria-hidden": true,
  width: 14,
  height: 14,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2.25,
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const;

// Ready-made icons for the four tones. Callers may pass their own.
export const StatusIcons = {
  leak: (
    <svg {...svgProps}>
      <path d="M12 5v10M7 11l5 5 5-5" />
    </svg>
  ),
  ok: (
    <svg {...svgProps}>
      <path d="m5 12.5 4.5 4.5L19 7.5" />
    </svg>
  ),
  flag: (
    <svg {...svgProps}>
      <path d="M6 20V4M6 5h11l-2 4 2 4H6" />
    </svg>
  ),
  info: (
    <svg {...svgProps}>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 11v5M12 8h.01" />
    </svg>
  ),
} as const;

export default function StatusPill({
  tone,
  label,
  icon,
  className,
}: {
  tone: StatusTone;
  label: string;
  icon: ReactNode;
  className?: string;
}) {
  // Types already require both. This guards untyped callers: a pill that
  // would rely on color alone renders nothing rather than ship inaccessibly.
  if (!label?.trim() || !icon) return null;
  return (
    <span
      data-status={tone}
      className={cx(
        "pk-small inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-1",
        TONES[tone],
        className,
      )}
    >
      {icon}
      <span>{label}</span>
    </span>
  );
}
