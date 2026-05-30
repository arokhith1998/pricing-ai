import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { cookies } from "next/headers";
import "./globals.css";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import AuroraBackground from "@/components/AuroraBackground";
import ScrollProgress from "@/components/ScrollProgress";
import { LEAD_COOKIE } from "@/lib/auth";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Pricekeel",
  description:
    "Stop discount leakage. Pricing intelligence for usage-based B2B SaaS.",
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  // Read the lead cookie server-side so Nav can render gated links in a
  // locked state before the click. The proxy still enforces the gate at
  // the route level; this is the visual contract for the navigation.
  const leadUnlocked = Boolean((await cookies()).get(LEAD_COOKIE)?.value);
  return (
    <html lang="en" className={`${inter.variable} antialiased`}>
      <body className="min-h-screen font-sans">
        <AuroraBackground />
        <ScrollProgress />
        <div aria-hidden className="pk-horizon" />
        <Nav leadUnlocked={leadUnlocked} />
        {children}
        <Footer />
      </body>
    </html>
  );
}
