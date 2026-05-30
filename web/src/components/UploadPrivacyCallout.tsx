// /upload page header callout — answers the first CFO question
// from the 2026-05-30 expert review: "What happens to my CSV?"
//
// Surfaces the privacy contract AT the upload moment, not buried in a
// /trust page click-through. Shield icon + three concrete promises +
// NDA offer + link to full security posture.

import Link from "next/link";

export default function UploadPrivacyCallout() {
  return (
    <section
      aria-label="What happens to your CSV"
      className="rounded-xl border border-teal/40 bg-surface-2 p-5"
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden
          className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-teal/50 bg-surface text-teal"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            <path d="M9 12l2 2 4-4" />
          </svg>
        </span>
        <div className="min-w-0">
          <div className="text-sm font-semibold text-fg">
            What happens to your CSV the moment you upload
          </div>
          <ul className="mt-2 space-y-1 text-sm text-muted">
            <li>
              <span className="text-teal">·</span>{" "}
              <span className="text-ink">Processed in memory.</span> The file is
              never written to disk on our servers and never persisted after
              the analysis completes.
            </li>
            <li>
              <span className="text-teal">·</span>{" "}
              <span className="text-ink">Row-level data does not leave the server.</span>{" "}
              Our cloud LLM only ever sees aggregate figures and your column
              header names — not the values in your rows.
            </li>
            <li>
              <span className="text-teal">·</span>{" "}
              <span className="text-ink">Not used to train any model.</span>{" "}
              We operate under zero-retention provider terms with our LLM
              vendor; your data does not enter their training data.
            </li>
            <li>
              <span className="text-teal">·</span>{" "}
              <span className="text-ink">NDA available.</span> If you need a
              signed NDA before sending data, email{" "}
              <a className="text-teal underline" href="mailto:adhithya@pricekeel.com">
                adhithya@pricekeel.com
              </a>{" "}
              and we will sign yours or send ours.
            </li>
          </ul>
          <div className="mt-2 text-[11px] text-muted">
            Full details:{" "}
            <Link className="text-teal underline" href="/trust">
              /trust
            </Link>{" "}
            ·{" "}
            <Link className="text-teal underline" href="/privacy">
              /privacy
            </Link>{" "}
            ·{" "}
            <Link className="text-teal underline" href="/subprocessors">
              /subprocessors
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
