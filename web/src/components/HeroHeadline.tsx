"use client";

import { useSyncExternalStore } from "react";
import { motion, useReducedMotion, type Variants } from "framer-motion";

const EASE = [0.22, 1, 0.36, 1] as const;

// "Have we hydrated yet" without calling setState in an effect: the server and
// the first client render both read false, every render after hydration reads
// true. No external state actually changes, so the subscribe is a no-op.
const noop = () => () => {};
function useHydrated(): boolean {
  return useSyncExternalStore(
    noop,
    () => true,
    () => false,
  );
}

// Hero headline with a word-by-word reveal (de-blur + rise) and a coral glow on
// the closing clause.
//
// SSR / LCP note: the server (and the pre-hydration client) renders a plain,
// fully visible <h1> so the headline paints immediately and survives with JS
// disabled. The framer-motion entrance only mounts after hydration, so content
// is never hidden at opacity 0 waiting for JavaScript. Under
// prefers-reduced-motion we keep the static headline permanently.
const WORDS = ["Stop", "giving", "away", "price", "that", "wins", "you", "nothing."];

const H1_CLASS =
  "mx-auto max-w-3xl text-4xl font-extrabold leading-[1.08] tracking-tight text-fg sm:text-5xl";

const wordClass = (w: string) =>
  `mr-[0.25em] inline-block ${w === "nothing." ? "pk-headline-accent text-coral" : ""}`;

export default function HeroHeadline() {
  const reduce = useReducedMotion();
  const mounted = useHydrated();

  // Server render + first client render (hydration match) + reduced motion:
  // a static, visible headline. No inline opacity, no dependency on JS.
  if (!mounted || reduce) {
    return (
      <h1 className={H1_CLASS}>
        {WORDS.map((w, i) => (
          <span key={i} className={wordClass(w)}>
            {w}
          </span>
        ))}
      </h1>
    );
  }

  const container: Variants = {
    hidden: {},
    show: {
      transition: { staggerChildren: 0.055, delayChildren: 0.05 },
    },
  };
  const word: Variants = {
    hidden: { opacity: 0, y: 20, filter: "blur(8px)" },
    show: {
      opacity: 1,
      y: 0,
      filter: "blur(0px)",
      transition: { duration: 0.6, ease: EASE },
    },
  };

  return (
    <motion.h1
      variants={container}
      initial="hidden"
      animate="show"
      className={H1_CLASS}
    >
      {WORDS.map((w, i) => (
        <motion.span key={i} variants={word} className={wordClass(w)}>
          {w}
        </motion.span>
      ))}
    </motion.h1>
  );
}
