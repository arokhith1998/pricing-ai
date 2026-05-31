"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

const ROLE_FUNCTIONS = [
  "Pricing",
  "Finance",
  "Sales / Revenue",
  "RevOps / Deal Desk",
  "Product",
  "Founder / Exec",
  "Other",
];

const ARR_RANGES = [
  "<$10M",
  "$10M to $50M",
  "$50M to $200M",
  "$200M+",
];

const PRICING_MODELS = [
  "Seats / per-user",
  "Usage / consumption",
  "Hybrid (platform + usage)",
  "Other",
];

// `next` is the route to send the user to after a successful submit. /sample
// passes it when proxy.ts redirected here with ?unlock=<route>, so the user
// lands on the page they originally clicked instead of staring at /sample.
export default function LeadForm({ next }: { next?: string } = {}) {
  const router = useRouter();
  const params = useSearchParams();
  const [f, setF] = useState({
    name: "",
    company: "",
    role_title: "",
    role_function: "",
    email: "",
    revenue_range: "",
    pricing_model: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [consent, setConsent] = useState(false);

  // Capture UTM tags from the URL; the API stores them with the lead so
  // LinkedIn / blog / outbound attribution actually works. Derived from the
  // URL on every render (no setState-in-effect; React 19 lints it).
  const utm = useMemo<Record<string, string>>(() => {
    const out: Record<string, string> = {};
    for (const k of ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"]) {
      const v = params.get(k);
      if (v) out[k] = v;
    }
    return out;
  }, [params]);

  const set =
    (k: keyof typeof f) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setF((prev) => ({ ...prev, [k]: e.target.value }));

  // Two-step progressive disclosure: don't show the ARR/pricing-model selects
  // until the four core fields are filled. Cuts the visible "wall of fields"
  // the marketer flagged without losing qualifying data.
  const coreReady =
    f.name.trim() && f.company.trim() && f.role_title.trim() && f.role_function.trim();
  const ready = Object.values(f).every((v) => v.trim().length > 0) && consent;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const res = await fetch("/api/lead", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...f, consent, utm }),
    });
    if (res.ok) {
      // If proxy.ts bounced us to /sample with ?unlock=<route>, send the
      // user back to that route now that the pk_lead cookie is set. Falls
      // back to refresh() so the on-page sample expands in place.
      if (next) {
        router.push(next);
      } else {
        router.refresh();
      }
    } else {
      const body = await res.json().catch(() => ({}));
      setError(body.error || "Something went wrong.");
      setBusy(false);
    }
  }

  const input =
    "w-full rounded-lg border border-mist bg-surface px-3 py-2 text-sm text-ink focus:border-teal focus:outline-none";

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <input className={input} placeholder="Full name" value={f.name} onChange={set("name")} />
        <input className={input} placeholder="Company" value={f.company} onChange={set("company")} />
        <input
          className={input}
          placeholder="Title (e.g. VP Pricing)"
          value={f.role_title}
          onChange={set("role_title")}
        />
        <select
          className={`${input} ${f.role_function ? "" : "text-slate"}`}
          value={f.role_function}
          onChange={set("role_function")}
        >
          <option value="" disabled>
            Role function
          </option>
          {ROLE_FUNCTIONS.map((r) => (
            <option key={r} value={r} className="text-ink">
              {r}
            </option>
          ))}
        </select>
      </div>
      <input
        className={input}
        type="email"
        placeholder="Company email"
        value={f.email}
        onChange={set("email")}
      />
      {coreReady ? (
        <div className="grid animate-in grid-cols-1 gap-3 sm:grid-cols-2">
          <select
            className={`${input} ${f.revenue_range ? "" : "text-slate"}`}
            value={f.revenue_range}
            onChange={set("revenue_range")}
          >
            <option value="" disabled>
              Annual revenue
            </option>
            {ARR_RANGES.map((r) => (
              <option key={r} value={r} className="text-ink">
                {r}
              </option>
            ))}
          </select>
          <select
            className={`${input} ${f.pricing_model ? "" : "text-slate"}`}
            value={f.pricing_model}
            onChange={set("pricing_model")}
          >
            <option value="" disabled>
              Pricing model
            </option>
            {PRICING_MODELS.map((p) => (
              <option key={p} value={p} className="text-ink">
                {p}
              </option>
            ))}
          </select>
        </div>
      ) : null}
      <label className="flex items-start gap-2 text-xs text-muted">
        <input
          type="checkbox"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          className="mt-0.5 h-4 w-4 shrink-0 accent-teal"
        />
        <span>
          I agree to the{" "}
          <a href="/privacy" target="_blank" className="text-teal underline">
            Privacy Policy
          </a>{" "}
          and to being contacted about my results.
        </span>
      </label>
      {error ? <p className="text-sm text-coral">{error}</p> : null}
      <button
        type="submit"
        disabled={busy || !ready}
        className="w-full rounded-lg bg-navy px-4 py-2.5 font-medium text-white transition hover:bg-navy/90 disabled:opacity-50"
      >
        {busy ? "Unlocking…" : "Unlock the full diagnostic"}
      </button>
      <p className="text-center text-xs text-slate">
        We use this to follow up about your results. Company email only.
      </p>
    </form>
  );
}
