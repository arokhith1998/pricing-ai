"use client";

import { useState } from "react";

// Small recovery form rendered under the main lead form on /sample.
// Solves "I submitted yesterday but I'm locked out again" without forcing
// a re-fill. Behavior:
//
//   1. User enters their email and submits.
//   2. POST /api/lead/magic-link looks them up in the database. If found,
//      emails a signed URL valid for 24 hours.
//   3. Response is always `{ ok: true }` regardless (no email enumeration).
//   4. UI swaps to "Check your inbox" and disables further submissions.

export default function MagicLinkForm({ next }: { next?: string } = {}) {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const res = await fetch("/api/lead/magic-link", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, next }),
    });
    if (res.ok) {
      setSent(true);
    } else {
      const body = await res.json().catch(() => ({}));
      setError(body.error || "Could not send the link. Try again.");
      setBusy(false);
    }
  }

  if (sent) {
    return (
      <div className="mt-6 rounded-lg border border-teal/40 bg-surface-2 p-4 text-sm text-fg">
        <span className="font-semibold text-teal">Check your inbox.</span>{" "}
        If we have a lead for that email, we just sent you a link. It is valid
        for 24 hours.
      </div>
    );
  }

  return (
    <div className="mt-6 rounded-lg border border-mist bg-surface-2 p-4">
      <div className="text-sm font-semibold text-fg">
        Already filled this out?
      </div>
      <p className="mt-1 text-xs text-muted">
        New device or cookies cleared? Enter your company email and we will
        send you a one-click link.
      </p>
      <form onSubmit={submit} className="mt-3 flex flex-col gap-2 sm:flex-row">
        <input
          className="w-full rounded-lg border border-mist bg-surface px-3 py-2 text-sm text-ink focus:border-teal focus:outline-none"
          type="email"
          placeholder="you@yourcompany.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <button
          type="submit"
          disabled={busy || !email}
          className="rounded-lg bg-navy px-4 py-2 text-sm font-medium text-white transition hover:bg-navy/90 disabled:opacity-50 sm:shrink-0"
        >
          {busy ? "Sending..." : "Send me a link"}
        </button>
      </form>
      {error ? <p className="mt-2 text-xs text-coral">{error}</p> : null}
    </div>
  );
}
