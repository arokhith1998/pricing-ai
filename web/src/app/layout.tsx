import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import ChromeEffects from "@/components/ChromeEffects";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });

const DEFAULT_TITLE = "Pricekeel · Salesforce deal guidance for B2B SaaS";
const DEFAULT_DESCRIPTION =
  "Pricekeel prices every discount exception in Salesforce before approval and records the decision with evidence Finance can audit, for usage and hybrid B2B SaaS.";

export const metadata: Metadata = {
  metadataBase: new URL("https://www.pricekeel.com"),
  title: {
    default: DEFAULT_TITLE,
    template: "%s · Pricekeel",
  },
  description: DEFAULT_DESCRIPTION,
  openGraph: {
    type: "website",
    siteName: "Pricekeel",
    url: "/",
    title: DEFAULT_TITLE,
    description: DEFAULT_DESCRIPTION,
  },
  twitter: {
    card: "summary_large_image",
    title: DEFAULT_TITLE,
    description: DEFAULT_DESCRIPTION,
  },
};

/*
 * MAIN LANDMARK CONTRACT (for every page task)
 *
 * This layout renders the skip link, the chrome, the header and the footer. It
 * does NOT render <main>: each page renders exactly one, as its root element:
 *
 *   <main id="main" tabIndex={-1}>...</main>
 *
 *  - id="main" is the skip link target (href="#main"). tabIndex={-1} lets the
 *    browser move focus there after the jump.
 *  - One <main> per page, one <h1> inside it (use ui/PageHeader).
 *  - Do not nest a second <main> and do not wrap pages in one from a layout.
 *  - Until a page sets the id itself, ChromeEffects adds it on the client so
 *    the link works everywhere; that shim is removed in PK-84.
 *  - Set page metadata with pageMetadata() from lib/page-metadata.ts. Pass the
 *    bare title: the "%s · Pricekeel" template above adds the brand.
 */
export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} antialiased`}>
      <body className="min-h-screen font-sans">
        <a
          href="#main"
          className="sr-only z-50 rounded-control bg-teal px-4 py-3 text-small font-semibold text-bg focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
        >
          Skip to content
        </a>
        <ChromeEffects />
        <div aria-hidden className="pk-horizon" />
        <Nav />
        {children}
        <Footer />
        {process.env.NEXT_PUBLIC_VERCEL_ANALYTICS_ENABLED === "true" ? (
          <Analytics />
        ) : null}
      </body>
    </html>
  );
}
