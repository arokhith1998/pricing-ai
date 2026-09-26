"use client";

import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";

// AuroraBackground and ScrollProgress are framer-motion scroll listeners with
// no product function; they are decorative chrome for the marketing pages.
// web/CLAUDE.md says static legal routes should stay dependency-free and
// fast, and those are exactly the pages a compliance reviewer opens first.
//
// Loaded with next/dynamic (not a static import) so each becomes its own
// chunk instead of folding framer-motion into the shared layout bundle every
// route pays for. Server-side rendering is left on (no ssr:false) so the
// marketing pages keep rendering the aurora/scroll-bar markup on first paint,
// exactly as before this change; only the static legal routes below skip
// rendering (and therefore fetching) the chunk at all.
const AuroraBackground = dynamic(() => import("./AuroraBackground"));
const ScrollProgress = dynamic(() => import("./ScrollProgress"));

const NO_CHROME_ROUTES = ["/privacy", "/terms", "/licenses", "/subprocessors"];

export default function ChromeEffects() {
  const pathname = usePathname();
  if (NO_CHROME_ROUTES.includes(pathname)) return null;
  return (
    <>
      <AuroraBackground />
      <ScrollProgress />
    </>
  );
}
