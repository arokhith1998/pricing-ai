"use client";

import { usePathname } from "next/navigation";
import { GLOBAL_DISCLOSURE, isAppRoute } from "@/lib/site-nav";

// The one global provenance line. Hidden on app routes, which can show a
// customer's own data, where "not customer data" would be untrue.
export default function FooterDisclosure() {
  const pathname = usePathname();
  if (isAppRoute(pathname)) return null;
  return <p className="pk-small text-fg">{GLOBAL_DISCLOSURE}</p>;
}
