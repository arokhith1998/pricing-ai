"use client";

import { motion, useScroll, useTransform } from "framer-motion";

// Three aurora layers translated at different rates as the page scrolls.
// Different y rates create perceived depth (far moves slowest, near fastest)
// without any WebGL. CSS keyframes on the layers add slow drift in place.
// All gated by prefers-reduced-motion via the override in globals.css.
export default function AuroraBackground() {
  const { scrollYProgress } = useScroll();
  const yFar = useTransform(scrollYProgress, [0, 1], ["0%", "-15%"]);
  const yMid = useTransform(scrollYProgress, [0, 1], ["0%", "-40%"]);
  const yNear = useTransform(scrollYProgress, [0, 1], ["0%", "-70%"]);

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    >
      <motion.div style={{ y: yFar }} className="pk-aurora-layer pk-aurora-far" />
      <motion.div style={{ y: yMid }} className="pk-aurora-layer pk-aurora-mid" />
      <motion.div
        style={{ y: yNear }}
        className="pk-aurora-layer pk-aurora-near"
      />
    </div>
  );
}
