// Single source for site navigation: the header, the mobile menu and the
// footer all read from here, so a link is added or renamed in one place.

export type NavLink = { href: string; label: string };

// PK-116 (F17): one offer, one call to action. The header is the logo, two
// links and the booking button. Every page's primary button reads from
// BOOKING_LABEL and BOOKING_URL, so the calendar link is changed in one place (PK-117, F18).
export const BOOKING_LABEL = "Book a 20-minute call";
export const BOOKING_URL = "https://calendly.com/adhithya-pricekeel/30min";

export const PRIMARY_NAV: readonly NavLink[] = [
  { href: "/audit", label: "Audit" },
  { href: "/contact", label: "Contact" },
];

export const PRIMARY_CTA: NavLink = { href: BOOKING_URL, label: BOOKING_LABEL };

export type FooterColumn = { title: string; links: readonly NavLink[] };

// Three links, one column. Subprocessors is linked from the text of /trust and
// /privacy; the unlinked pages stay reachable by direct URL only.
export const FOOTER_COLUMNS: readonly FooterColumn[] = [
  {
    title: "Trust and legal",
    links: [
      { href: "/trust", label: "Trust" },
      { href: "/privacy", label: "Privacy" },
      { href: "/terms", label: "Terms" },
    ],
  },
];

export const GLOBAL_DISCLOSURE =
  "Figures on this site come from a synthetic 2,000-deal sample or are illustrative. None is customer data.";

/**
 * The global disclosure is shown only on the unlinked routes that still carry
 * synthetic or illustrative figures. No linked page carries one.
 */
export const DISCLOSURE_ROUTES: readonly string[] = [
  "/sample",
  "/calculator",
  "/diagnostic",
  "/guidance",
  "/methodology",
  "/blog",
];

export function showsDisclosure(pathname: string): boolean {
  return DISCLOSURE_ROUTES.some((r) => pathname === r || pathname.startsWith(`${r}/`));
}

/** Routes with no decorative chrome at all (static legal pages). */
export const NO_CHROME_ROUTES: readonly string[] = ["/privacy", "/terms", "/licenses", "/subprocessors"];

/** Long-form routes that get the CSS scroll-progress bar. */
export function showsScrollProgress(pathname: string): boolean {
  return pathname.startsWith("/blog/") || pathname === "/methodology" || pathname === "/trust";
}

/**
 * aria-current="page" rule. Hash links (the Product anchor) are never the
 * current page: the wordmark carries aria-current on "/". Other links match
 * their path exactly or as a parent of the current path.
 */
export function isCurrent(pathname: string, href: string): boolean {
  if (href.includes("#")) return false;
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}
