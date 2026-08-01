"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRef } from "react";

function KeelMark() {
  return (
    <svg width="34" height="34" viewBox="0 0 64 64" aria-label="Pricekeel">
      <line x1="10" y1="26" x2="54" y2="26" stroke="#e9f0f8" strokeWidth="3" strokeLinecap="round" opacity="0.88" />
      <path d="M 14 26 Q 34 60 50 26" fill="none" stroke="#2dd4bf" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const LINKS = [
  { href: "/#workflow", label: "Product" },
  { href: "/sample", label: "Live sample" },
  { href: "/pricing", label: "Pricing" },
  { href: "/trust", label: "Trust" },
] as const;

function isActive(pathname: string, href: string) {
  if (href.startsWith("/#")) return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function MarketingLinks({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <>
      {LINKS.map((link) => {
        const active = isActive(pathname, link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
              active ? "bg-mist text-fg" : "text-slate hover:bg-mist hover:text-fg"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
      <Link
        href="/crm"
        onClick={onNavigate}
        className="rounded-lg border border-teal/50 px-3 py-2 text-sm font-semibold text-teal transition hover:bg-teal/10"
      >
        Customer workspace
      </Link>
    </>
  );
}

export default function Nav() {
  const pathname = usePathname();
  const mobileMenu = useRef<HTMLDetailsElement>(null);

  return (
    <header className="sticky top-0 z-30 border-b border-mist bg-surface/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link href="/" className="flex shrink-0 items-center gap-2.5" aria-label="Pricekeel home">
          <KeelMark />
          <div>
            <div className="text-xl font-extrabold leading-none tracking-tight">
              <span className="text-fg">Price</span><span className="text-teal">keel</span>
            </div>
            <div className="mt-0.5 hidden text-[11px] text-slate lg:block">
              Pricing decisions, kept on course.
            </div>
          </div>
        </Link>

        <nav aria-label="Primary" className="hidden items-center gap-1 md:flex">
          <MarketingLinks pathname={pathname} />
        </nav>

        <details ref={mobileMenu} className="group relative md:hidden">
          <summary className="flex cursor-pointer list-none items-center gap-2 rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm font-medium text-fg marker:hidden">
            Menu
            <svg aria-hidden className="transition group-open:rotate-180" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="m6 9 6 6 6-6" />
            </svg>
          </summary>
          <nav aria-label="Mobile primary" className="absolute right-0 top-[calc(100%+0.6rem)] z-40 flex w-64 flex-col gap-1 rounded-xl border border-mist bg-surface p-2 shadow-2xl shadow-black/40">
            <MarketingLinks
              pathname={pathname}
              onNavigate={() => {
                // Let the link complete its native navigation before hiding
                // the <details> subtree. Closing it synchronously can remove
                // the clicked anchor from hit-testing before navigation.
                window.setTimeout(() => mobileMenu.current?.removeAttribute("open"), 0);
              }}
            />
          </nav>
        </details>
      </div>
    </header>
  );
}
