import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacy Policy · Pricekeel" };

// NOTE TO FOUNDER: this is an accurate description of what the app does today
// AND covers the 11 substantive gaps the 2026-05-30 legal audit identified
// (subprocessor disclosure, legal basis per purpose, transfer mechanism, DSAR
// procedure, retention schedule, security measures, AI Act transparency, CCPA
// section, children's exclusion, AI-specific disclosures, DPA availability).
// It is NOT legal advice. Fill the [bracketed] entity/jurisdiction fields and
// have a lawyer review before relying on it.

const EFFECTIVE = "30 May 2026";
const CONTACT = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "[privacy@pricekeel.com]";

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="mt-8">
      <h2 className="text-lg font-semibold text-fg">{title}</h2>
      <div className="mt-2 space-y-3 text-sm leading-relaxed text-muted">{children}</div>
    </section>
  );
}

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-3xl font-bold text-fg">Privacy Policy</h1>
      <p className="mt-2 text-sm text-muted">
        Effective {EFFECTIVE} ·{" "}
        <span className="inline-block rounded border border-coral/40 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-coral">
          DRAFT, counsel review pending
        </span>
      </p>

      <p className="mt-6 text-sm leading-relaxed text-muted">
        This policy explains what Pricekeel (&ldquo;we&rdquo;, operated by{" "}
        <span className="text-fg">[legal entity]</span>,{" "}
        <span className="text-fg">[jurisdiction]</span>) collects, why, and
        what we do with it. We keep data collection to the minimum needed to
        run the product, and we publish the full subprocessor list at{" "}
        <a className="text-teal underline" href="/subprocessors">/subprocessors</a>{" "}
        and the security posture at{" "}
        <a className="text-teal underline" href="/trust">/trust</a>.
      </p>

      <Section id="categories" title="What we collect and why">
        <p>
          <span className="font-medium text-fg">Contact details you give us.</span>{" "}
          When you request the full sample, we collect your name, company,
          job title, role function, company email address, revenue range,
          and pricing model. Optionally, UTM parameters from the URL you
          arrived on (no third-party advertising trackers).
          <br />
          <span className="text-fg">Legal basis (GDPR):</span> your consent
          (Art. 6(1)(a)) via the consent checkbox on the lead form.
        </p>
        <p>
          <span className="font-medium text-fg">Data you upload for analysis.</span>{" "}
          When you run the diagnostic on your own CSV or upload documents to
          the copilot, those files are processed in memory to compute your
          results and are then deleted. We do not store your uploaded deal
          data and do not use it to train any model.
          <br />
          <span className="text-fg">Legal basis (GDPR):</span> performance of
          the engagement we have with you (Art. 6(1)(b)) for paying
          customers, or your explicit consent (Art. 6(1)(a)) for ad-hoc use.
        </p>
        <p>
          <span className="font-medium text-fg">Access codes.</span> If you
          are issued an access code, we record it and when it is used.
          <br />
          <span className="text-fg">Legal basis (GDPR):</span> our legitimate
          interest in controlling access to non-public functionality (Art.
          6(1)(f)).
        </p>
        <p>
          <span className="font-medium text-fg">Pricing URLs you submit.</span>{" "}
          For the Competitor Watch feature, we fetch and analyze the
          competitor pricing URLs you enter. We honor robots.txt on the
          target site, maintain a kill-switch for any host that asks us to
          stop, and cache fetched content for no more than one hour.
        </p>
        <p>
          <span className="font-medium text-fg">Basic technical logs.</span>{" "}
          Standard server logs (e.g., IP address, request timestamp,
          user-agent) retained for security, fraud prevention, and
          reliability.
          <br />
          <span className="text-fg">Legal basis (GDPR):</span> legitimate
          interest in operating and securing the Service (Art. 6(1)(f)).
        </p>
      </Section>

      <Section id="ai" title="AI processing and transparency">
        <p>
          To generate the written summary, the copilot answers, the
          column-mapping suggestions, and the competitor-plan extractions,
          we send <span className="font-medium text-fg">aggregate analysis
          figures, column header names, document chunks you uploaded, your
          question text, and (for Competitor Watch) the public pricing-page
          text</span> to our cloud LLM provider (OpenAI). We do not send
          row-level deal data. The provider operates under a written
          data-processing addendum that prohibits the use of inputs and
          outputs for model training.
        </p>
        <p>
          Every recommendation surfaced by the Pricekeel copilot is
          generated by deterministic Python from the customer&rsquo;s own
          analysis. The cloud LLM only narrates the structured opportunities;
          it is forbidden in its system prompt from inventing numbers,
          companies, or plans. Each surfaced opportunity is logged with its
          supporting math so a CFO can audit it back to the source signal.
        </p>
        <p>
          This is an AI-assisted system within the meaning of the EU AI
          Act. We treat it as &ldquo;limited risk&rdquo; (informational,
          human-in-the-loop) and disclose AI involvement wherever it
          appears in the product.
        </p>
      </Section>

      <Section id="how-we-use" title="How we use it">
        <p>
          To provide the diagnostic and guidance, to deliver copilot
          answers grounded in your own analysis and documents, to extract
          and compare competitor plan structures you submit URLs for, to
          follow up with you about your results and the product, and to
          administer access. We do not sell or share personal information
          for third-party advertising, and we do not use uploaded deal or
          document data to train any model.
        </p>
      </Section>

      <Section id="who-we-share" title="Who we share it with">
        <p>
          We use a small set of subprocessors (hosting, database, LLM
          provider, email host, DNS). The full current list with regions
          and DPA links is at{" "}
          <a className="text-teal underline" href="/subprocessors">/subprocessors</a>.
          They process data only on our instructions and only to provide
          their service to us.
        </p>
        <p>
          For uploaded deal data shared during an engagement, a mutual
          non-disclosure agreement also governs handling. A Data Processing
          Addendum is available on request for business customers; email{" "}
          <a className="text-teal underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>.
        </p>
      </Section>

      <Section id="transfers" title="International data transfers">
        <p>
          All subprocessors are headquartered in the United States. Where
          personal data of individuals located in the EU/EEA, UK, or
          Switzerland is transferred to the United States, the transfer
          relies on the European Commission&rsquo;s Standard Contractual
          Clauses (SCCs) referenced in the relevant subprocessor DPA, and on
          the EU-U.S. Data Privacy Framework where the recipient is
          certified. A transfer impact assessment is available on request.
        </p>
      </Section>

      <Section id="cookies" title="Cookies">
        <p>
          We use two functional cookies, both strictly necessary to operate
          the Service: <code>pk_lead</code> (remembers that you have
          unlocked the sample diagnostic) and <code>pk_access</code>{" "}
          (remembers that you have entered a valid access code for your own
          data). We do not use advertising, retargeting, or cross-site
          tracking cookies, and we do not load third-party analytics that
          set cookies.
        </p>
      </Section>

      <Section id="retention" title="Retention schedule">
        <ul className="list-disc space-y-1 pl-6">
          <li>
            <span className="font-medium text-fg">Lead contact details:</span>{" "}
            24 months after your last interaction, then deleted unless you
            are a paying customer.
          </li>
          <li>
            <span className="font-medium text-fg">Access codes:</span> until
            revoked or 12 months after last use, whichever is sooner.
          </li>
          <li>
            <span className="font-medium text-fg">Uploaded CSV / document files:</span>{" "}
            zero. Files are processed in memory and not persisted after the
            analysis completes.
          </li>
          <li>
            <span className="font-medium text-fg">Cached competitor pricing-page content:</span>{" "}
            one hour maximum, in memory only.
          </li>
          <li>
            <span className="font-medium text-fg">Server logs:</span> 30 days.
          </li>
          <li>
            <span className="font-medium text-fg">Decision log of copilot recommendations:</span>{" "}
            for the duration of your active engagement, plus 12 months for
            audit purposes.
          </li>
        </ul>
      </Section>

      <Section id="security" title="Security measures (GDPR Art. 32)">
        <p>
          Encryption in transit (TLS 1.2+) on all endpoints. Encryption at
          rest on the database (AES-256 via Supabase). Secrets stored in
          encrypted environment-variable stores. Server-side service-role
          access only to the database; no anon key in the browser.
          Multi-factor authentication enforced on every admin account.
          Change management via GitHub pull requests with CI. Daily
          automated database backups. The full security posture is at{" "}
          <a className="text-teal underline" href="/trust">/trust</a>.
        </p>
      </Section>

      <Section id="rights" title="Your rights">
        <p>
          Depending on where you live (for example under GDPR, UK GDPR,
          CCPA / CPRA, PIPEDA, or LGPD), you may have the right to access,
          correct, delete, port, or object to processing of your personal
          information. To exercise these rights, email{" "}
          <a className="text-teal underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>{" "}
          with the subject line &ldquo;Data Subject Request&rdquo;. We will
          respond within 30 days. We may verify your identity before
          providing access to or deleting data.
        </p>
        <p>
          <span className="font-medium text-fg">California residents:</span>{" "}
          we do not sell or share personal information as defined by the
          CCPA / CPRA. You may exercise your right to know, to delete, and
          to correct using the email above.
        </p>
      </Section>

      <Section id="children" title="Children">
        <p>
          The Service is intended for business users and is not directed to
          individuals under 16. We do not knowingly collect personal data
          from anyone under 16. If you believe we have inadvertently done
          so, email{" "}
          <a className="text-teal underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>{" "}
          and we will delete it.
        </p>
      </Section>

      <Section id="breach" title="Breach notification">
        <p>
          In the event of a confirmed personal-data breach involving your
          data, we will notify the email address on file within 72 hours of
          becoming aware of the breach, and supervisory authorities where
          required by law.
        </p>
      </Section>

      <Section id="changes" title="Changes and contact">
        <p>
          We will post any changes to this policy here with an updated
          effective date. For paid customers, material changes will also be
          notified by email. Questions? Email{" "}
          <a className="text-teal underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>.
        </p>
      </Section>
    </main>
  );
}
