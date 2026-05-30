"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";

// Brand mark. Keeps the source-of-truth geometry inline so the nav stays
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

// Small padlock used in the locked nav state. Same stroke and corner radius
// as the rest of the nav iconography.
function LockIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      aria-hidden
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <rect x="4" y="11" width="16" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}

// Nav entries. `gated` links require a captured lead. When the visitor does
// not have the pk_lead cookie they render in a locked state: padlock icon,
// muted color, hover tooltip explaining how to unlock. Clicking still works
// and sends them to /sample with an unlock banner so they always have a
// next step.
type NavLink = {
  href: string;
  label: string;
  gated: boolean;
  unlockSlug?: string; // value passed as ?unlock= when locked
};

const LINKS: NavLink[] = [
  { href: "/sample", label: "Overview", gated: false },
  { href: "/diagnostic", label: "Diagnostic", gated: true, unlockSlug: "diagnostic" },
  { href: "/guidance", label: "Guidance", gated: true, unlockSlug: "guidance" },
  { href: "/competitor-watch", label: "Competitor watch", gated: true, unlockSlug: "competitor-watch" },
];

export default function Nav({ leadUnlocked = false }: { leadUnlocked?: boolean }) {
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
          {LINKS.map((link) => {
            const active =
              link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            const locked = link.gated && !leadUnlocked;

            // When locked, route the click to /sample with the unlock slug
            // so the user lands on the page that hosts the lead form, with
            // the banner naming what they were trying to open.
            const href = locked && link.unlockSlug
              ? `/sample?unlock=${link.unlockSlug}`
              : link.href;

            // Locked links use a wrapper so the tooltip can be a sibling
            // span positioned via group-hover. Active links are never
            // locked (active means the user is already on the page, which
            // means they had the cookie when proxy let them in).
            return (
              <div key={link.href} className="group relative">
                <Link
                  href={href}
                  aria-disabled={locked ? "true" : undefined}
                  className={`relative flex items-center gap-1.5 rounded-lg px-3 py-2 transition ${
                    !active && !locked ? "hover:bg-mist" : ""
                  } ${locked ? "cursor-pointer" : ""}`}
                >
                  {active ? (
                    <motion.span
                      layoutId="nav-pill"
                      className="absolute inset-0 rounded-lg bg-navy"
                      transition={{ type: "spring", stiffness: 500, damping: 38 }}
                    />
                  ) : null}
                  {locked ? (
                    <LockIcon className="relative text-slate/70 transition group-hover:text-teal" />
                  ) : null}
                  <span
                    className={`relative ${
                      active
                        ? "text-white"
                        : locked
                          ? "text-slate/70 transition group-hover:text-fg"
                          : "text-slate hover:text-fg"
                    }`}
                  >
                    {link.label}
                  </span>
                </Link>
                {locked ? (
                  <span
                    role="tooltip"
                    className="pointer-events-none absolute left-1/2 top-full z-20 mt-2 w-56 -translate-x-1/2 rounded-lg border border-mist bg-surface px-3 py-2 text-xs leading-snug text-fg opacity-0 shadow-lg transition group-hover:opacity-100"
                  >
                    <span className="font-semibold text-teal">Locked.</span>{" "}
                    Fill the short unlock form on the Overview page to open
                    the {link.label.toLowerCase()} view.
                    <span
                      aria-hidden
                      className="absolute -top-1 left-1/2 h-2 w-2 -translate-x-1/2 rotate-45 border-l border-t border-mist bg-surface"
                    />
                  </span>
                ) : null}
              </div>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
