"use client";

import { motion, useScroll, useSpring } from "framer-motion";

// Thin teal bar that tracks page scroll progress. Tasteful, premium.
export default function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, {
    stiffness: 220,
    damping: 30,
    mass: 0.3,
  });
  return (
    <motion.div
      aria-hidden
      className="fixed left-0 right-0 top-0 z-50 h-0.5 origin-left bg-teal"
      style={{ scaleX }}
    />
  );
}
