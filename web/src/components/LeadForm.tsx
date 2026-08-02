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

// Client-side mirror of the free-email domain list in @/lib/auth (server).
// Kept as a copy because auth.ts also holds server-only cookie/secret logic
// we must not pull into the client bundle. If you change one, change both.
const FREE_EMAIL_DOMAINS = new Set([
  "gmail.com", "googlemail.com", "yahoo.com", "ymail.com", "outlook.com",
  "hotmail.com", "live.com", "msn.com", "icloud.com", "me.com", "mac.com",
  "aol.com", "proton.me", "protonmail.com", "pm.me", "gmx.com", "mail.com",
  "yandex.com", "zoho.com", "hey.com", "fastmail.com",
]);

function isCompanyEmail(email: string): boolean {
  const m = /^[^\s@]+@([^\s@]+\.[^\s@]+)$/.exec(email.trim().toLowerCase());
  if (!m) return false;
  return !FREE_EMAIL_DOMAINS.has(m[1]);
}

// The server route (/api/lead) still requires every field to be non-empty.
// Until that contract is loosened, blank optional fields are sent with these
// sentinel defaults so the form does not 400. See the route for the required
// check; another change owns cleaning this up.
const OPTIONAL_DEFAULTS = {
  name: "Not provided",
  role_title: "Not provided",
  role_function: "Other",
  revenue_range: "Unknown",
  pricing_model: "Unknown",
} as const;

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
  const [emailError, setEmailError] = useState("");
  const [busy, setBusy] = useState(false);
  const [consent, setConsent] = useState(false);
  // Honeypot for the server's bot check: humans never see this field, bots
  // that autofill every input do. The API silently drops submissions where
  // it is non-empty.
  const [website, setWebsite] = useState("");

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

  // Mirror the server's business-email check on blur, so a gmail address is
  // caught before the round-trip rather than after.
  function validateEmail() {
    const v = f.email.trim();
    if (v && !isCompanyEmail(v)) {
      setEmailError(
        "Please use your company email address (personal domains like gmail.com are not accepted).",
      );
    } else {
      setEmailError("");
    }
  }

  // Only company email + company + consent are required. Everything else is
  // optional context. The two-step reveal is flattened: with two required
  // fields, progressive disclosure hid nothing worth hiding.
  const emailOk = isCompanyEmail(f.email);
  const ready = emailOk && f.company.trim().length > 0 && consent;

  // One-line hint naming the first missing requirement while the button is
  // disabled.
  const missingHint = !f.email.trim()
    ? "Still needed: your company email."
    : !emailOk
      ? "Still needed: a valid company email (not a personal domain)."
      : !f.company.trim()
        ? "Still needed: your company name."
        : !consent
          ? "Still needed: tick the consent box."
          : "";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    let res: Response;
    try {
      res = await fetch("/api/lead", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...f,
          // Blank optional fields get sentinel defaults; the server route
          // still 400s on empty strings (see OPTIONAL_DEFAULTS note above).
          name: f.name.trim() || OPTIONAL_DEFAULTS.name,
          role_title: f.role_title.trim() || OPTIONAL_DEFAULTS.role_title,
          role_function: f.role_function || OPTIONAL_DEFAULTS.role_function,
          revenue_range: f.revenue_range || OPTIONAL_DEFAULTS.revenue_range,
          pricing_model: f.pricing_model || OPTIONAL_DEFAULTS.pricing_model,
          website,
          consent,
          utm,
        }),
      });
    } catch {
      setError("Could not reach the server. Check your connection and try again.");
      setBusy(false);
      return;
    }
    if (res.ok) {
      // The response has set the signed lead cookie. Move directly into the
      // requested surface; a direct sample unlock defaults to Diagnostic so
      // the visitor is never left wondering what changed on /sample.
      router.replace(next || "/diagnostic");
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
      {/* Honeypot: visually hidden, removed from tab order and a11y tree. */}
      <input
        type="text"
        name="website"
        value={website}
        onChange={(e) => setWebsite(e.target.value)}
        tabIndex={-1}
        autoComplete="off"
        aria-hidden="true"
        className="absolute -left-[9999px] h-0 w-0 opacity-0"
      />
      <input
        className={`${input} ${emailError ? "border-coral/60" : ""}`}
        type="email"
        placeholder="Company email"
        value={f.email}
        onChange={(e) => {
          set("email")(e);
          if (emailError) setEmailError("");
        }}
        onBlur={validateEmail}
        aria-invalid={emailError ? "true" : undefined}
      />
      {emailError ? <p className="text-xs text-coral">{emailError}</p> : null}
      <input
        className={input}
        placeholder="Company"
        value={f.company}
        onChange={set("company")}
      />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <input
          className={input}
          placeholder="Full name (optional)"
          value={f.name}
          onChange={set("name")}
        />
        <input
          className={input}
          placeholder="Title, e.g. VP Pricing (optional)"
          value={f.role_title}
          onChange={set("role_title")}
        />
        <select
          className={`${input} ${f.role_function ? "" : "text-slate"}`}
          value={f.role_function}
          onChange={set("role_function")}
        >
          <option value="" disabled>
            Role function (optional)
          </option>
          {ROLE_FUNCTIONS.map((r) => (
            <option key={r} value={r} className="text-ink">
              {r}
            </option>
          ))}
        </select>
        <select
          className={`${input} ${f.revenue_range ? "" : "text-slate"}`}
          value={f.revenue_range}
          onChange={set("revenue_range")}
        >
          <option value="" disabled>
            Annual revenue (optional)
          </option>
          {ARR_RANGES.map((r) => (
            <option key={r} value={r} className="text-ink">
              {r}
            </option>
          ))}
        </select>
        <select
          className={`${input} ${f.pricing_model ? "" : "text-slate"} sm:col-span-2`}
          value={f.pricing_model}
          onChange={set("pricing_model")}
        >
          <option value="" disabled>
            Pricing model (optional)
          </option>
          {PRICING_MODELS.map((p) => (
            <option key={p} value={p} className="text-ink">
              {p}
            </option>
          ))}
        </select>
      </div>
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
      {!ready && !busy && missingHint ? (
        <p className="text-center text-xs text-slate">{missingHint}</p>
      ) : null}
      <p className="text-center text-xs text-slate">
        We use this to follow up about your results. Company email only.
      </p>
    </form>
  );
}
