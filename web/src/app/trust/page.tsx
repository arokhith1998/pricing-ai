import type { Metadata } from "next";

export const metadata: Metadata = { title: "Trust & Security · Pricekeel" };

// NOTE TO FOUNDER: this page describes Pricekeel's security posture as of
// today. Update when SOC 2 readiness moves, when a new control lands, when
// you change a vendor, or when an incident happens. Honesty beats marketing
// here — pricing teams' IT reviewers will read this carefully.

const EFFECTIVE = "30 May 2026";
const CONTACT = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "[security@pricekeel.com]";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-8">
      <h2 className="text-lg font-semibold text-fg">{title}</h2>
      <div className="mt-2 space-y-3 text-sm leading-relaxed text-muted">{children}</div>
    </section>
  );
}

export default function TrustPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-3xl font-bold text-fg">Trust &amp; Security</h1>
      <p className="mt-2 text-sm text-muted">
        Updated {EFFECTIVE} ·{" "}
        <span className="inline-block rounded border border-mist px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-muted">
          Pre-SOC&nbsp;2 · controls live
        </span>
      </p>

      <p className="mt-6 text-sm leading-relaxed text-muted">
        Pricekeel handles pricing-strategy data — the kind a CFO and a Head
        of Pricing both have opinions about. This page describes how we
        keep it safe, with no marketing-grade hedging. If anything here
        does not match what you need for your IT review, email{" "}
        <a className="text-teal underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>{" "}
        and we will tell you straight.
      </p>

      <Section title="Where the data lives">
        <ul className="list-disc space-y-1 pl-6">
          <li>
            <span className="font-medium text-fg">Web (pricekeel.com)</span>{" "}
            — Vercel, United States (us-east-1) with global edge.
          </li>
          <li>
            <span className="font-medium text-fg">API (api.pricekeel.com)</span>{" "}
            — Render, United States (Virginia).
          </li>
          <li>
            <span className="font-medium text-fg">Database (leads + access codes)</span>{" "}
            — Supabase Postgres, United States (us-east-1).
          </li>
        </ul>
        <p>
          The complete subprocessor list with DPA links is at{" "}
          <a className="text-teal underline" href="/subprocessors">/subprocessors</a>.
        </p>
      </Section>

      <Section title="What we do NOT store">
        <ul className="list-disc space-y-1 pl-6">
          <li>
            Row-level deal data uploaded for diagnostics is processed in
            memory and not persisted after the analysis completes.
          </li>
          <li>
            Documents you upload to the copilot are chunked + embedded in
            memory; raw documents are not written to disk on the API
            server.
          </li>
          <li>
            Competitor pricing pages are cached for a maximum of one hour
            in memory only, never persisted.
          </li>
          <li>
            We do not use Customer Data to train any model, and our LLM
            providers operate under zero-retention terms for the data we
            send them.
          </li>
        </ul>
      </Section>

      <Section title="Encryption">
        <ul className="list-disc space-y-1 pl-6">
          <li>
            <span className="font-medium text-fg">In transit:</span> TLS 1.2+
            enforced everywhere (HSTS preload-eligible, no plaintext
            endpoints).
          </li>
          <li>
            <span className="font-medium text-fg">At rest:</span> Supabase
            encrypts the database at rest by default (AES-256). Render and
            Vercel encrypt their storage volumes at rest.
          </li>
          <li>
            Secrets (API keys, database service-role key, app signing
            secret) are stored in Vercel/Render encrypted environment
            variable stores and never appear in the codebase.
          </li>
        </ul>
      </Section>

      <Section title="Access control">
        <ul className="list-disc space-y-1 pl-6">
          <li>
            Only the founder has admin access to production infrastructure
            (Vercel, Render, Supabase, GoDaddy DNS). MFA enforced on every
            account.
          </li>
          <li>
            The Supabase database is reached server-side only with the
            service-role key. The browser-side anon key is not exposed and
            no public client has direct database access.
          </li>
          <li>
            Two-tier funnel gate: the captured-lead cookie unlocks the
            sample diagnostic; the access-code cookie unlocks customer
            data upload. Access codes are issued only after a signed NDA.
          </li>
        </ul>
      </Section>

      <Section title="AI handling">
        <ul className="list-disc space-y-1 pl-6">
          <li>
            The cloud LLM (OpenAI) sees only aggregate analysis figures,
            column header names, the document chunks you upload, your
            question text, and (for competitor watch) the public pricing-
            page text you submit. <strong>Row-level deal data is never
            sent to the cloud LLM.</strong>
          </li>
          <li>
            Recommendations are generated by deterministic Python code; the
            LLM only narrates them. Every dollar figure traces to a key in
            the analysis dict — the LLM is forbidden in its system prompt
            from inventing numbers.
          </li>
          <li>
            Every decision the copilot surfaces is logged with its
            supporting math, so a CFO can audit any recommendation back to
            the source signal.
          </li>
        </ul>
      </Section>

      <Section title="Operational controls">
        <ul className="list-disc space-y-1 pl-6">
          <li>
            <span className="font-medium text-fg">Change management:</span>{" "}
            every production change ships through a GitHub pull request
            with a CI build. The main branch deploys automatically; preview
            branches deploy to isolated URLs.
          </li>
          <li>
            <span className="font-medium text-fg">Backups:</span> Supabase
            performs automated daily backups. Code is mirrored on GitHub.
          </li>
          <li>
            <span className="font-medium text-fg">Monitoring:</span> Render
            health-check probes /health every minute. Error tracking is in
            implementation; this page will be updated when it lands.
          </li>
          <li>
            <span className="font-medium text-fg">Incident response:</span>{" "}
            we will notify affected customers within 72 hours of becoming
            aware of a confirmed breach involving their data. Notification
            goes to the email address on file.
          </li>
        </ul>
      </Section>

      <Section title="Compliance posture">
        <ul className="list-disc space-y-1 pl-6">
          <li>
            <span className="font-medium text-fg">GDPR + UK GDPR:</span>{" "}
            data subject rights honored; Standard Contractual Clauses in
            place via subprocessor DPAs; lawful basis for lead-form data is
            consent.
          </li>
          <li>
            <span className="font-medium text-fg">CCPA / CPRA:</span> we do
            not sell or share personal information.
          </li>
          <li>
            <span className="font-medium text-fg">EU AI Act:</span> the
            Pricekeel diagnostic and copilot are informational systems with
            human-in-the-loop decision-making; we treat them as
            &ldquo;limited risk&rdquo; under the Act and disclose AI
            involvement everywhere it appears.
          </li>
          <li>
            <span className="font-medium text-fg">SOC 2:</span> not yet
            certified. The controls described above are implemented;
            external Type I audit is planned once the customer base
            supports the spend.
          </li>
          <li>
            <span className="font-medium text-fg">HIPAA / PCI / FedRAMP:</span>{" "}
            not in scope. We do not process protected health information,
            cardholder data, or U.S. government data.
          </li>
        </ul>
      </Section>

      <Section title="Vulnerability disclosure">
        <p>
          If you believe you have found a security vulnerability in
          Pricekeel, please email{" "}
          <a className="text-teal underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>{" "}
          rather than disclosing it publicly. We will acknowledge within
          two business days and work with you on a coordinated disclosure.
          We do not yet offer a paid bug bounty.
        </p>
      </Section>
    </main>
  );
}
