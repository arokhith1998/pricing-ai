"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

// Optional: set NEXT_PUBLIC_CONTACT_EMAIL to surface a "request access" mailto.
const CONTACT_EMAIL = process.env.NEXT_PUBLIC_CONTACT_EMAIL;

function KeelMark() {
  return (
    <svg width="40" height="40" viewBox="0 0 48 48" aria-hidden>
      <line x1="9" y1="19" x2="39" y2="19" stroke="#0c2d48" strokeWidth="3" strokeLinecap="round" />
      <path d="M13 19 Q24 43 35 19" fill="none" stroke="#17b8a6" strokeWidth="4" strokeLinecap="round" />
    </svg>
  );
}

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/";
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const res = await fetch("/api/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    if (res.ok) {
      router.replace(next);
      router.refresh();
    } else {
      const body = await res.json().catch(() => ({}));
      setError(body.error || "Could not sign in.");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="w-full max-w-sm space-y-4">
      <input
        type="password"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="Access code"
        autoFocus
        className="w-full rounded-lg border border-mist bg-white px-3 py-2 text-ink focus:border-teal focus:outline-none"
      />
      {error ? <p className="text-sm text-coral">{error}</p> : null}
      <button
        type="submit"
        disabled={busy || !code}
        className="w-full rounded-lg bg-navy px-4 py-2 font-medium text-white transition hover:bg-navy/90 disabled:opacity-50"
      >
        {busy ? "Checking…" : "Enter"}
      </button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <main className="mx-auto flex min-h-[70vh] max-w-6xl flex-col items-center justify-center px-6">
      <div className="mb-2 flex items-center gap-3">
        <KeelMark />
        <div className="text-2xl font-extrabold tracking-tight">
          <span className="text-navy">Price</span>
          <span className="text-teal">keel</span>
        </div>
      </div>
      <p className="mb-6 text-sm text-slate">
        Enter your access code to run Pricekeel on your own data.
      </p>
      <Suspense>
        <LoginForm />
      </Suspense>
      <p className="mt-6 max-w-sm text-center text-xs text-slate">
        Don&apos;t have a code? {CONTACT_EMAIL ? (
          <a
            className="font-medium text-navy underline"
            href={`mailto:${CONTACT_EMAIL}?subject=Pricekeel%20access%20request`}
          >
            Request access
          </a>
        ) : (
          "Ask your Pricekeel contact"
        )}{" "}
        — we will sign an NDA before you share any data.
      </p>
    </main>
  );
}
