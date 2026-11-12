"use client";

import { usePathname } from "next/navigation";
import { GLOBAL_DISCLOSURE, showsDisclosure } from "@/lib/site-nav";

// The one global provenance line. Shown only on the unlinked routes that carry
// synthetic or illustrative figures; no linked page has one.
export default function FooterDisclosure() {
  const pathname = usePathname();
  if (!showsDisclosure(pathname)) return null;
  return <p className="pk-small text-fg">{GLOBAL_DISCLOSURE}</p>;
}
