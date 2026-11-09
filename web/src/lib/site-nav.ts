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

export const CUSTOMER_LOGIN: NavLink = { href: "/login", label: "Customer login" };
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
      { href: "/login", label: "Login" },
      { href: "/crm", label: "Salesforce workspace" },
      { href: "/upload", label: "Run it on your data" },
    ],
  },
];

export const GLOBAL_DISCLOSURE =
  "Every figure on this site comes from a synthetic 2,000-deal sample, not customer data.";

/**
 * Routes where the global disclosure is hidden. These screens can show a
 * customer's own data (uploads, the Salesforce workspace), so the sentence
 * "not customer data" would be false there.
 */
export const APP_ROUTES: readonly string[] = [
  "/crm",
  "/upload",
  "/diagnostic",
  "/guidance",
  "/competitor-watch",
];

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
