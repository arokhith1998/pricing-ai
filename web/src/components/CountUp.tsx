"use client";

import { useEffect, useState } from "react";
import { animate, useMotionValue, useReducedMotion } from "framer-motion";
import { money, moneyShort, pct } from "@/lib/format";

// Formatters resolved by key so the server can hand props (numbers + strings)
// to this client component without crossing the function-serialization boundary.
const FORMATTERS = {
  money,
  moneyShort,
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
  const reduce = useReducedMotion();
  const m = useMotionValue(0);
  const [animated, setAnimated] = useState(fmt(0));
  // The effect only drives the animation, and only when motion is allowed, so
  // it never calls setState synchronously in its own body. Under
  // prefers-reduced-motion the effect is a no-op and the final value is
  // computed during render instead.
  useEffect(() => {
    if (reduce) return;
    const unsub = m.on("change", (latest) => setAnimated(fmt(latest)));
    const ctrl = animate(m, to, { duration, ease: [0.22, 1, 0.36, 1] });
    return () => {
      ctrl.stop();
      unsub();
    };
  }, [to, fmt, duration, m, reduce]);
  // Under reduced motion, show the final value immediately; otherwise show the
  // animating value.
  const v = reduce ? fmt(to) : animated;
  // Final value to assistive tech via a visually-hidden span; the animated
  // text is decorative (aria-hidden). aria-label on a role-less span is
  // prohibited by ARIA, so we expose the value as real (sr-only) text instead.
  return (
    <span>
      <span aria-hidden="true">{v}</span>
      <span className="sr-only">{fmt(to)}</span>
    </span>
  );
}
