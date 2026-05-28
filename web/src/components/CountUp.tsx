"use client";

import { useEffect, useState } from "react";
import { animate, useMotionValue } from "framer-motion";
import { money, pct } from "@/lib/format";

// Formatters resolved by key so the server can hand props (numbers + strings)
// to this client component without crossing the function-serialization boundary.
const FORMATTERS = {
  money,
  pct,
  integer: (n: number) => Math.round(n).toLocaleString(),
} as const;
export type CountUpFormat = keyof typeof FORMATTERS;

// Animate a number from 0 to `to`, formatted via the chosen built-in formatter.
// ~1.2s with an easeOutExpo-ish curve. Tasteful "count-up" for headline KPIs.
export default function CountUp({
  to,
  format = "money",
  duration = 1.2,
}: {
  to: number;
  format?: CountUpFormat;
  duration?: number;
}) {
  const fmt = FORMATTERS[format];
  const m = useMotionValue(0);
  const [v, setV] = useState(fmt(0));
  useEffect(() => {
    const unsub = m.on("change", (latest) => setV(fmt(latest)));
    const ctrl = animate(m, to, { duration, ease: [0.22, 1, 0.36, 1] });
    return () => {
      ctrl.stop();
      unsub();
    };
  }, [to, fmt, duration, m]);
  // Final value to assistive tech via aria-label; animated text is decorative.
  return (
    <span aria-label={fmt(to)}>
      <span aria-hidden="true">{v}</span>
    </span>
  );
}
