"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const ROLE_FUNCTIONS = [
  "Pricing",
  "Finance",
  "Sales / Revenue",
  "RevOps / Deal Desk",
  "Product",
  "Founder / Exec",
  "Other",
];

export default function LeadForm() {
  const router = useRouter();
  const [f, setF] = useState({
    name: "",
    company: "",
    role_title: "",
    role_function: "",
    email: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setF((prev) => ({ ...prev, [k]: e.target.value }));

  const ready = Object.values(f).every((v) => v.trim().length > 0);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const res = await fetch("/api/lead", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(f),
    });
    if (res.ok) {
      router.refresh(); // re-render the server component; pk_lead now unlocks it
    } else {
      const body = await res.json().catch(() => ({}));
      setError(body.error || "Something went wrong.");
      setBusy(false);
    }
  }

  const input =
    "w-full rounded-lg border border-mist bg-white px-3 py-2 text-sm text-ink focus:border-teal focus:outline-none";

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
