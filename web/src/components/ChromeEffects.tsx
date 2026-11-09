"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import AuroraBackground from "./AuroraBackground";
import ScrollProgress from "./ScrollProgress";
import { NO_CHROME_ROUTES, showsScrollProgress } from "@/lib/site-nav";

// Decorative chrome, all static or CSS only. The static legal routes get none
// of it. The scroll bar renders only on long-form routes.
export default function ChromeEffects() {
  const pathname = usePathname();

  // Transitional: the skip link targets #main (contract in layout.tsx). Pages
  // that have not adopted <main id="main"> yet get the id here so the link
  // works on every route. PK-84 removes this once every page sets it.
  useEffect(() => {
    const main = document.querySelector("main");
    if (main && !main.id) {
      main.id = "main";
      main.setAttribute("tabindex", "-1");
    }
  }, [pathname]);

  if (NO_CHROME_ROUTES.includes(pathname)) return null;
  return (
    <>
      <AuroraBackground />
      {showsScrollProgress(pathname) ? <ScrollProgress /> : null}
    </>
  );
}
