import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import AuroraBackground from "@/components/AuroraBackground";
import ScrollProgress from "@/components/ScrollProgress";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });

const DEFAULT_TITLE = "Pricekeel · Salesforce discount intelligence for B2B SaaS";
const DEFAULT_DESCRIPTION =
  "Connect Salesforce, analyze discount behavior and price realization, and bring auditable recommendations into the deal-approval workflow.";

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
        <AuroraBackground />
        <ScrollProgress />
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
