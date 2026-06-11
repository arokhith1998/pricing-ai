"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";

const EASE = [0.22, 1, 0.36, 1] as const;

// Hero headline with a word-by-word reveal (de-blur + rise) and a coral glow on
// the closing clause. Animates on mount — it is the first thing in view. The
// whole effect collapses to a clean static headline under prefers-reduced-motion.
const WORDS = ["Stop", "giving", "away", "price", "that", "wins", "you", "nothing."];

export default function HeroHeadline() {
  const reduce = useReducedMotion();

  const container: Variants = {
    hidden: {},
    show: {
      transition: { staggerChildren: reduce ? 0 : 0.055, delayChildren: reduce ? 0 : 0.05 },
    },
  };
  const word: Variants = {
    hidden: reduce ? { opacity: 1 } : { opacity: 0, y: 20, filter: "blur(8px)" },
    show: {
      opacity: 1,
      y: 0,
      filter: "blur(0px)",
      transition: { duration: reduce ? 0 : 0.6, ease: EASE },
    },
  };

  return (
    <motion.h1
      variants={container}
      initial="hidden"
      animate="show"
      className="mx-auto max-w-3xl text-4xl font-extrabold leading-[1.08] tracking-tight text-fg sm:text-5xl"
    >
      {WORDS.map((w, i) => {
        const accent = w === "nothing.";
        return (
          <motion.span
            key={i}
            variants={word}
            className={`mr-[0.25em] inline-block ${accent ? "pk-headline-accent text-coral" : ""}`}
          >
            {w}
          </motion.span>
        );
      })}
    </motion.h1>
  );
}
