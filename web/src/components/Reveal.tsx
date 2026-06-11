"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";
import type { ReactNode } from "react";

const EASE = [0.22, 1, 0.36, 1] as const;

// Subtle, professional section reveal: fade + slight rise.
//
// Default mode animates on mount (content must never be stuck invisible below
// the fold). Pass `inView` to defer the reveal until the element scrolls into
// view — the cinematic scroll-cascade used down the landing page. Both modes
// honor prefers-reduced-motion: motion collapses to an instant appear.
export default function Reveal({
  children,
  delay = 0,
  className,
  inView = false,
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
  inView?: boolean;
}) {
  const reduce = useReducedMotion();
  const initial = reduce ? { opacity: 1, y: 0 } : { opacity: 0, y: 12 };
  const shown = { opacity: 1, y: 0 };
  const transition = { duration: reduce ? 0 : 0.5, delay: reduce ? 0 : delay, ease: EASE };

  if (inView) {
    return (
      <motion.div
        className={className}
        initial={initial}
        whileInView={shown}
        viewport={{ once: true, margin: "-80px" }}
        transition={transition}
      >
        {children}
      </motion.div>
    );
  }
  return (
    <motion.div
      className={className}
      initial={initial}
      animate={shown}
      transition={transition}
    >
      {children}
    </motion.div>
  );
}

// --- Staggered grids --------------------------------------------------------
// Wrap a grid in <Stagger> and each cell in <StaggerItem>; children cascade in
// as the grid scrolls into view. Reduced-motion collapses the stagger to 0.

export function Stagger({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const container: Variants = {
    hidden: {},
    show: {
      transition: { staggerChildren: reduce ? 0 : 0.08, delayChildren: reduce ? 0 : 0.05 },
    },
  };
  return (
    <motion.div
      className={className}
      variants={container}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-60px" }}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const item: Variants = {
    hidden: reduce ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 },
    show: { opacity: 1, y: 0, transition: { duration: reduce ? 0 : 0.5, ease: EASE } },
  };
  return (
    <motion.div className={className} variants={item}>
      {children}
    </motion.div>
  );
}
