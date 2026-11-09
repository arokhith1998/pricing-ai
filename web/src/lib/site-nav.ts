// Single source for site navigation: the header, the mobile menu and the
// footer all read from here, so a link is added or renamed in one place.

export type NavLink = { href: string; label: string };

export const PRIMARY_NAV: readonly NavLink[] = [
  { href: "/#workflow", label: "Product" },
  { href: "/sample", label: "Sample" },
  { href: "/calculator", label: "Calculator" },
  { href: "/pricing", label: "Pricing" },
  { href: "/trust", label: "Trust" },
];

// Links to /crm on purpose: the proxy sends an unauthenticated visitor to
// /login?next=/crm, and a signed-in customer lands in the workspace. The
// /login route itself is matched for aria-current separately (CUSTOMER_LOGIN_ALSO).
export const CUSTOMER_LOGIN: NavLink = { href: "/crm", label: "Customer login" };
export const CUSTOMER_LOGIN_ALSO = "/login";
export const PRIMARY_CTA: NavLink = { href: "/contact", label: "Talk to us" };

export type FooterColumn = { title: string; links: readonly NavLink[] };

export const FOOTER_COLUMNS: readonly FooterColumn[] = [
  {
    title: "Product",
    links: [
      { href: "/sample", label: "Sample" },
      { href: "/calculator", label: "Calculator" },
      { href: "/pricing", label: "Pricing" },
      { href: "/methodology", label: "Methodology" },
    ],
  },
  {
    title: "Company",
    links: [
      { href: "/contact", label: "Contact" },
      { href: "/blog", label: "Blog" },
      { href: "/brand", label: "Brand" },
    ],
  },
  {
    title: "Trust and legal",
    links: [
      { href: "/trust", label: "Trust" },
      { href: "/privacy", label: "Privacy" },
      { href: "/terms", label: "Terms" },
      { href: "/subprocessors", label: "Subprocessors" },
      { href: "/licenses", label: "Licenses" },
    ],
  },
  {
    title: "Customers",
    links: [
      { href: "/crm", label: "Login" },
      { href: "/crm", label: "Salesforce workspace" },
      { href: "/upload", label: "Run it on your data" },
    ],
  },
];

export const GLOBAL_DISCLOSURE =
  "Figures on this site come from a synthetic 2,000-deal sample or are illustrative. None is customer data.";

/**
 * Routes where the global disclosure is hidden: they can show a customer's own
 * data (uploads, the Salesforce workspace) or public competitor pages, so
 * "None is customer data" would not hold. /diagnostic and /guidance show the
 * synthetic sample and carry the line. (Lead decision, PR 87 review.)
 */
export const APP_ROUTES: readonly string[] = ["/crm", "/upload", "/competitor-watch"];

/** Routes with no decorative chrome at all (static legal pages). */
export const NO_CHROME_ROUTES: readonly string[] = ["/privacy", "/terms", "/licenses", "/subprocessors"];

/** Long-form routes that get the CSS scroll-progress bar. */
export function showsScrollProgress(pathname: string): boolean {
  return pathname.startsWith("/blog/") || pathname === "/methodology" || pathname === "/trust";
}

export function isAppRoute(pathname: string): boolean {
  return APP_ROUTES.some((r) => pathname === r || pathname.startsWith(`${r}/`));
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

/** aria-current for the Customer login link: it points at /crm but /login counts too. */
export function isCustomerLoginCurrent(pathname: string): boolean {
  return isCurrent(pathname, CUSTOMER_LOGIN.href) || isCurrent(pathname, CUSTOMER_LOGIN_ALSO);
}
