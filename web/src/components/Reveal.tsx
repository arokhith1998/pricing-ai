"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";

const EASE = [0.22, 1, 0.36, 1] as const;

// 2026-09-27 external review: the live /pricing hero rendered as an empty
// viewport for some visitors. Root cause: Reveal/Stagger bake their hidden
// state (opacity 0, translateY) into the server-rendered HTML via framer
// motion's `initial`, and only ever remove it once an IntersectionObserver
// (or, for mount-mode, hydration itself) actually fires. Some visitors never
// get there: headless audit tools, certain in-app browsers, a zero-height
// ancestor, or JS that fails before hydration completes. Those visitors saw
// permanently hidden content.
//
// Fix: SSR and the very first client paint always render the plain, fully
// visible markup below (`Plain`), with no inline opacity ever shipped in the
// static HTML. Only after mounting do we "arm" the entrance animation, and
// only when there is something to reveal:
//   - reduced motion: never arm, stay visible.
//   - `inView` content already sitting in the viewport at mount: never arm,
//     stay visible (there is nothing for the visitor to see appear).
//   - otherwise: arm the animation, and if the viewport observer has not
//     fired within FALLBACK_MS, force the visible state anyway rather than
//     leave the section hidden forever.
const FALLBACK_MS = 800;

const shown = { opacity: 1, y: 0 };
const hidden = { opacity: 0, y: 12 };

function isOnScreen(el: HTMLElement) {
  const rect = el.getBoundingClientRect();
  return rect.top < window.innerHeight && rect.bottom > 0;
}

// Plain, unanimated wrapper: what SSR renders, what the first client paint
// renders, and what a reduced-motion or already-visible visitor keeps
// rendering forever. Deliberately not a motion component, so it never ships
// an inline opacity/transform.
function Plain({
  className,
  innerRef,
  children,
}: {
  className?: string;
  innerRef: React.RefObject<HTMLDivElement | null>;
  children: ReactNode;
}) {
  return (
    <div ref={innerRef} className={className}>
      {children}
    </div>
  );
}

// Arms the entrance animation once JS has hydrated, unless reduced motion is
// on, or (for `inView` mode) the element is already visible on screen. Also
// arms an ~800ms forced-visible fallback so a viewport observer that never
// fires cannot hide content permanently.
function useArm(inView: boolean) {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const enteredRef = useRef(false);
  const [armed, setArmed] = useState(false);
  const [forced, setForced] = useState(false);

  useEffect(() => {
    if (reduce) return;
    if (inView && ref.current && isOnScreen(ref.current)) return;
    setArmed(true);
  }, [reduce, inView]);

  useEffect(() => {
    if (!armed || !inView || forced) return;
    const timer = window.setTimeout(() => {
      if (!enteredRef.current) setForced(true);
    }, FALLBACK_MS);
    return () => window.clearTimeout(timer);
  }, [armed, inView, forced]);

  const onViewportEnter = () => {
    enteredRef.current = true;
  };

  return { ref, active: armed && !forced, onViewportEnter };
}

// Subtle, professional section reveal: fade + slight rise.
//
// Default mode animates on mount (content must never be stuck invisible
// below the fold). Pass `inView` to defer the reveal until the element
// scrolls into view — the cinematic scroll-cascade used down the landing
// page. Both modes honor prefers-reduced-motion: motion collapses to an
// instant appear.
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
  const transition = { duration: reduce ? 0 : 0.5, delay: reduce ? 0 : delay, ease: EASE };
  const { ref, active, onViewportEnter } = useArm(inView);

  if (!active) {
    return (
      <Plain className={className} innerRef={ref}>
        {children}
      </Plain>
    );
  }

  if (inView) {
    return (
      <motion.div
        ref={ref}
        className={className}
        initial={hidden}
        whileInView={shown}
        viewport={{ once: true, amount: 0, margin: "0px 0px -10% 0px" }}
        transition={transition}
        onViewportEnter={onViewportEnter}
      >
        {children}
      </motion.div>
    );
  }
  return (
    <motion.div
      ref={ref}
      className={className}
      initial={hidden}
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
// Shares the arm/fallback/already-visible guard above via StaggerArmedContext
// so a StaggerItem never renders hidden unless its Stagger parent actually
// armed the animation.

const StaggerArmedContext = createContext(false);

export function Stagger({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const { ref, active, onViewportEnter } = useArm(true);
  const container: Variants = {
    hidden: {},
    show: {
      transition: { staggerChildren: reduce ? 0 : 0.08, delayChildren: reduce ? 0 : 0.05 },
    },
  };

  if (!active) {
    return (
      <StaggerArmedContext.Provider value={false}>
        <Plain className={className} innerRef={ref}>
          {children}
        </Plain>
      </StaggerArmedContext.Provider>
    );
  }

  return (
    <StaggerArmedContext.Provider value={true}>
      <motion.div
        ref={ref}
        className={className}
        variants={container}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0, margin: "0px 0px -10% 0px" }}
        onViewportEnter={onViewportEnter}
      >
        {children}
      </motion.div>
    </StaggerArmedContext.Provider>
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
  const armed = useContext(StaggerArmedContext);
  const item: Variants = {
    hidden: reduce ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 },
    show: { opacity: 1, y: 0, transition: { duration: reduce ? 0 : 0.5, ease: EASE } },
  };

  if (!armed) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div className={className} variants={item}>
      {children}
    </motion.div>
  );
}
