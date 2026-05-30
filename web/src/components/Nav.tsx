"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";

// Brand mark — keeps the source-of-truth geometry inline so the nav stays
// crisp at any zoom, while the same geometry also lives at /brand/logo-mark.svg
// for downloads, social avatars, and external use.
function KeelMark() {
  return (
    <svg width="34" height="34" viewBox="0 0 64 64" aria-label="Pricekeel">
      <line
        x1="10" y1="26" x2="54" y2="26"
        stroke="#e9f0f8" strokeWidth="3"
        strokeLinecap="round" opacity="0.88"
      />
      <path
        d="M 14 26 Q 34 60 50 26"
        fill="none" stroke="#2dd4bf"
        strokeWidth="5"
        strokeLinecap="round" strokeLinejoin="round"
      />
    </svg>
  );
}

const LINKS: [string, string][] = [
  ["/sample", "Overview"],
  ["/diagnostic", "Diagnostic"],
  ["/guidance", "Guidance"],
  ["/competitor-watch", "Competitor watch"],
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-10 border-b border-mist bg-surface/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
        <Link href="/" className="flex items-center gap-3">
          <KeelMark />
          <div>
            <div className="text-xl font-extrabold tracking-tight leading-none">
              <span className="text-fg">Price</span>
              <span className="text-teal">keel</span>
            </div>
            <div className="mt-0.5 text-xs text-slate">
              Keep your pricing on an even keel.
            </div>
          </div>
        </Link>
        <nav className="flex items-center gap-1 text-sm font-medium">
          {LINKS.map(([href, label]) => {
            const active =
              href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`relative rounded-lg px-3 py-2 transition ${
                  !active ? "hover:bg-mist" : ""
                }`}
              >
                {active ? (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 rounded-lg bg-navy"
                    transition={{ type: "spring", stiffness: 500, damping: 38 }}
                  />
                ) : null}
                <span
                  className={`relative ${
                    active ? "text-white" : "text-slate hover:text-fg"
                  }`}
                >
                  {label}
                </span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
