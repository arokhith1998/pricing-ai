"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

// Subtle, professional section reveal: fade + slight rise as it scrolls in.
export default function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  // Animate on mount (not whileInView): content must never be stuck invisible
  // below the fold if it is not scrolled into view.
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}
