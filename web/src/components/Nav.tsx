"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRef } from "react";
import { buttonClasses } from "@/components/ui/Button";
import { CUSTOMER_LOGIN, PRIMARY_CTA, PRIMARY_NAV, isCurrent } from "@/lib/site-nav";

function KeelMark() {
  return (
    <svg width="34" height="34" viewBox="0 0 64 64" aria-label="Pricekeel">
      <line x1="10" y1="26" x2="54" y2="26" stroke="#e9f0f8" strokeWidth="3" strokeLinecap="round" opacity="0.88" />
      <path d="M 14 26 Q 34 60 50 26" fill="none" stroke="#2dd4bf" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

type LinkProps = { pathname: string; onNavigate?: () => void; mobile?: boolean };

function PrimaryLinks({ pathname, onNavigate, mobile }: LinkProps) {
  return (
    <>
      {PRIMARY_NAV.map((link) => {
        const current = isCurrent(pathname, link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            onClick={onNavigate}
            aria-current={current ? "page" : undefined}
            className={`rounded-control text-small font-medium transition ${
              mobile ? "flex min-h-12 items-center px-3" : "px-3 py-2"
            } ${current ? "bg-border text-fg" : "text-muted hover:bg-border hover:text-fg"}`}
          >
            {link.label}
          </Link>
        );
      })}
    </>
  );
}

function AccountLinks({ pathname, onNavigate, mobile }: LinkProps) {
  const login = isCurrent(pathname, CUSTOMER_LOGIN.href);
  const cta = isCurrent(pathname, PRIMARY_CTA.href);
  return (
    <>
      <Link
        href={CUSTOMER_LOGIN.href}
        onClick={onNavigate}
        aria-current={login ? "page" : undefined}
        className={`rounded-control text-small font-medium transition ${
          mobile ? "flex min-h-12 items-center px-3" : "px-3 py-2"
        } ${login ? "text-fg" : "text-muted hover:text-fg"}`}
      >
        {CUSTOMER_LOGIN.label}
      </Link>
      <Link
        href={PRIMARY_CTA.href}
        onClick={onNavigate}
        aria-current={cta ? "page" : undefined}
        className={buttonClasses("primary", "md", mobile ? "min-h-12 w-full" : undefined)}
      >
        {PRIMARY_CTA.label}
      </Link>
    </>
  );
}

export default function Nav() {
  const pathname = usePathname();
  const mobileMenu = useRef<HTMLDetailsElement>(null);
  const home = isCurrent(pathname, "/");

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-surface/95 backdrop-blur">
      <div className="mx-auto flex max-w-page items-center justify-between gap-4 px-gutter py-3 sm:px-gutter-lg">
        <Link
          href="/"
          className="flex shrink-0 items-center gap-2.5"
          aria-label="Pricekeel home"
          aria-current={home ? "page" : undefined}
        >
          <KeelMark />
          <div>
            <div className="text-xl font-extrabold leading-none tracking-tight">
              <span className="text-fg">Price</span>
              <span className="text-teal">keel</span>
            </div>
            <div className="pk-micro mt-0.5 hidden text-muted xl:block">
              Pricing decisions, kept on course.
            </div>
          </div>
        </Link>

        <nav aria-label="Primary" className="hidden items-center gap-1 lg:flex">
          <PrimaryLinks pathname={pathname} />
        </nav>
        <div className="hidden items-center gap-2 lg:flex">
          <AccountLinks pathname={pathname} />
        </div>

        {/* Mobile and tablet: a native <details> sheet, so it opens and closes
            with JavaScript disabled. Rows are 48px tall. */}
        <details ref={mobileMenu} className="group lg:hidden">
          <summary className="pk-control flex cursor-pointer list-none items-center gap-2 text-small font-medium marker:hidden">
            Menu
            <svg aria-hidden className="transition group-open:rotate-180" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="m6 9 6 6 6-6" />
            </svg>
          </summary>
          <nav
            aria-label="Mobile primary"
            className="absolute inset-x-0 top-full z-40 flex max-h-[calc(100dvh-4.5rem)] flex-col gap-1 overflow-y-auto border-b border-border bg-surface p-3 shadow-2xl shadow-black/40"
          >
            <PrimaryLinks
              mobile
              pathname={pathname}
              onNavigate={() => {
                // Let the link complete its native navigation before hiding
                // the <details> subtree; closing synchronously can remove the
                // clicked anchor from hit-testing before navigation.
                window.setTimeout(() => mobileMenu.current?.removeAttribute("open"), 0);
              }}
            />
            <div className="mt-2 flex flex-col gap-1 border-t border-border pt-3">
              <AccountLinks
                mobile
                pathname={pathname}
                onNavigate={() => {
                  window.setTimeout(() => mobileMenu.current?.removeAttribute("open"), 0);
                }}
              />
            </div>
          </nav>
        </details>
      </div>
    </header>
  );
}
