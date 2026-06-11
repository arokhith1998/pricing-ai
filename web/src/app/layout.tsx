import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { cookies } from "next/headers";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import AuroraBackground from "@/components/AuroraBackground";
import ScrollProgress from "@/components/ScrollProgress";
import { LEAD_COOKIE, verifyLeadCookieValue } from "@/lib/auth";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });

const DEFAULT_TITLE = "Pricekeel · Discount leakage diagnostic for B2B SaaS";
const DEFAULT_DESCRIPTION =
  "Find the discount leakage hiding in your closed-won deals. A diagnostic for usage-based B2B SaaS: every dollar figure tied to its math, defensible to finance.";

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
  // Read the lead cookie server-side so Nav can render gated links in a
  // locked state before the click. The proxy still enforces the gate at
  // the route level; this is the visual contract for the navigation.
  // Verify the signature so a self-granted pk_lead=1 stays locked.
  const leadUnlocked = await verifyLeadCookieValue(
    (await cookies()).get(LEAD_COOKIE)?.value,
  );
  return (
    <html lang="en" className={`${inter.variable} antialiased`}>
      <body className="min-h-screen font-sans">
        <AuroraBackground />
        <ScrollProgress />
        <div aria-hidden className="pk-horizon" />
        <Nav leadUnlocked={leadUnlocked} />
        {children}
        <Footer />
        <Analytics />
      </body>
    </html>
  );
}
