"use client";

import { useEffect } from "react";

// Reads a `?ref=` token from the URL on first paint and logs a landing hit
// through /api/link-click, so a cold-outreach link like
// pricekeel.com/?ref=temporal-interview is attributable to the company or
// campaign it came from. Deliberately reads window.location directly
// (not next/navigation's useSearchParams) so this stays a plain client-side
// effect with no Suspense boundary requirement and no effect on force-static
// rendering of the pages it sits on.
//
// Rendered once in the root layout, gated by
// NEXT_PUBLIC_LINK_TRACKING_ENABLED (see .env.example). No PII: the ref is
// a short token the founder chooses per link, not a person or email.

const REF_PARAM = "ref";
const UTM_KEYS = ["utm_source", "utm_medium", "utm_campaign"] as const;

// Same shape the API enforces: short, URL-safe, no free text.
const SAFE_TOKEN = /^[a-zA-Z0-9_-]{1,64}$/;

export default function LinkClickCapture() {
  useEffect(() => {
    if (typeof window === "undefined") return;

    const params = new URLSearchParams(window.location.search);
    const ref = params.get(REF_PARAM);
    if (!ref || !SAFE_TOKEN.test(ref)) return;

    // Once per browser tab session per ref: a visitor clicking through
    // several internal pages after landing should not produce a row per
    // page. A fresh tab (new outreach click, or the same link reopened
    // later) logs again, which is what we want for attribution.
    const dedupeKey = `pk_ref_logged:${ref}`;
    try {
      if (window.sessionStorage.getItem(dedupeKey)) return;
    } catch {
      // sessionStorage can throw in locked-down browser contexts; fall
      // through and log anyway rather than silently dropping the hit.
    }

    const utm: Record<string, string> = {};
    for (const k of UTM_KEYS) {
      const v = params.get(k);
      if (v) utm[k] = v;
    }

    fetch("/api/link-click", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ref,
        landing_path: window.location.pathname,
        utm,
      }),
      keepalive: true,
    }).catch(() => {
      /* best-effort; never surface a failure to the visitor */
    });

    try {
      window.sessionStorage.setItem(dedupeKey, "1");
    } catch {
      /* best-effort dedupe only */
    }
  }, []);

  return null;
}
