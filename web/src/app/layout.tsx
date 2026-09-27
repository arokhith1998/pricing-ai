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

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} antialiased`}>
      <body className="min-h-screen font-sans">
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
