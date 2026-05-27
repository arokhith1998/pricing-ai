"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

function KeelMark() {
  return (
    <svg width="32" height="32" viewBox="0 0 48 48" aria-hidden>
      <line x1="9" y1="19" x2="39" y2="19" stroke="#0c2d48" strokeWidth="3" strokeLinecap="round" />
      <path d="M13 19 Q24 43 35 19" fill="none" stroke="#17b8a6" strokeWidth="4" strokeLinecap="round" />
    </svg>
  );
}

const LINKS: [string, string][] = [
  ["/sample", "Overview"],
  ["/diagnostic", "Diagnostic"],
  ["/guidance", "Guidance"],
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-10 border-b border-mist bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
        <Link href="/" className="flex items-center gap-3">
          <KeelMark />
          <div>
            <div className="text-xl font-extrabold tracking-tight leading-none">
              <span className="text-navy">Price</span>
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
                className={`rounded-lg px-3 py-2 transition ${
                  active
                    ? "bg-navy text-white"
                    : "text-slate hover:bg-mist hover:text-navy"
                }`}
              >
                {label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
