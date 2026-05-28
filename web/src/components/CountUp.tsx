"use client";

import { useEffect, useState } from "react";
import { animate, useMotionValue } from "framer-motion";

// Animate a number from 0 (or `from`) to `to`, formatted via `format`.
// Tasteful "count-up" for headline metric values. ~1.2s, easeOutExpo-ish.
export default function CountUp({
  to,
  format,
  from = 0,
  duration = 1.2,
}: {
  to: number;
  format: (n: number) => string;
  from?: number;
  duration?: number;
}) {
  const m = useMotionValue(from);
  const [v, setV] = useState(format(from));
  useEffect(() => {
    const unsub = m.on("change", (latest) => setV(format(latest)));
    const ctrl = animate(m, to, { duration, ease: [0.22, 1, 0.36, 1] });
    return () => {
      ctrl.stop();
      unsub();
    };
  }, [to, format, duration, m]);
  // Give assistive tech the final value once; the animated text is decorative.
  return (
    <span aria-label={format(to)}>
      <span aria-hidden="true">{v}</span>
    </span>
  );
}
