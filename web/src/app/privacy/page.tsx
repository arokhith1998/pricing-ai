import type { Metadata } from "next";
import { LEGAL_ENTITY, LEGAL_JURISDICTION, ENTITY_FILLED } from "@/lib/legal";

export const metadata: Metadata = { title: "Privacy Policy" };

// NOTE TO FOUNDER: this is an accurate description of what the app does today
// AND covers the 11 substantive gaps the 2026-05-30 legal audit identified
// (subprocessor disclosure, legal basis per purpose, transfer mechanism, DSAR
// procedure, retention schedule, security measures, AI Act transparency, CCPA
// section, children's exclusion, AI-specific disclosures, DPA availability).
// It is NOT legal advice. Fill the [bracketed] entity/jurisdiction fields and
// have a lawyer review before relying on it.

const EFFECTIVE = "11 November 2026";
const CONTACT = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "adhithya@pricekeel.com";

// Until incorporation completes, name Pricekeel plainly instead of rendering
// "[legal entity], [jurisdiction]" placeholders to the public. Once the env
// vars in @/lib/legal are filled, the registered entity renders instead.
const ENTITY_DESCRIPTION = ENTITY_FILLED
  ? `${LEGAL_ENTITY}, ${LEGAL_JURISDICTION}`
  : "Pricekeel (US entity formation in progress; this policy will be updated with the registered entity name and jurisdiction)";

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
        Last updated {EFFECTIVE}. Under legal review. Questions:{" "}
        <a className="text-teal underline" href="mailto:adhithya@pricekeel.com">
          adhithya@pricekeel.com
        </a>
      </p>

      <p className="mt-6 text-sm leading-relaxed text-muted">
        This policy explains what{" "}
        <span className="text-fg">{ENTITY_DESCRIPTION}</span>{" "}
        (&ldquo;we&rdquo;) collects, why, and
        what we do with it. We keep data collection to the minimum needed to
        run the product, and we publish the full subprocessor list on our{" "}
        <a className="text-teal underline" href="/subprocessors">Subprocessors page</a>{" "}
        and the security posture on our{" "}
        <a className="text-teal underline" href="/trust">Trust page</a>.
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
          <span className="font-medium text-fg">Files you send for an audit.</span>{" "}
          After a mutual NDA and data addendum are signed, you send billing and cost
          exports with customers replaced by codes. We do not ask for API keys, system
          connections or end-user personal data. We use the files only to deliver your
          audit, and we delete them within 30 days of the engagement ending and confirm
          it in writing.
          <br />
          <span className="text-fg">Legal basis (GDPR):</span> performance of the
          engagement we have with you (Art. 6(1)(b)).
        </p>
        <p>
          <span className="font-medium text-fg">Access codes.</span> If you
          are issued an access code for a customer workspace, we record it and when it
          is used. The workspace is available only by direct invitation and is not part
          of the audit. Before you connect anything to it, we tell you in writing what
          it stores.
          <br />
          <span className="text-fg">Legal basis (GDPR):</span> our legitimate
          interest in controlling access to non-public functionality (Art.
          6(1)(f)).
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

      <Section id="ai" title="AI tools">
        <p>
          We may use AI tools in our work. Files you send for an audit are used only to
          deliver your audit. They are not used to improve models that benefit other
          customers without your written consent. The data addendum names the vendors
          that may process your files.
        </p>
      </Section>

      <Section id="how-we-use" title="How we use it">
        <p>
          To deliver your audit, to reply to you and follow up about it, and to
          administer access. We do not sell or share personal information for
          third-party advertising, and we do not use files you send to improve models
          that benefit other customers without your written consent.
        </p>
      </Section>

      <Section id="who-we-share" title="Who we share it with">
        <p>
          We use a small set of subprocessors (hosting, database, email, DNS). The full current list with regions
          and DPA links is on our{" "}
          <a className="text-teal underline" href="/subprocessors">Subprocessors page</a>.
          They process data only on our instructions and only to provide
          their service to us.
        </p>
        <p>
          For files shared during an engagement, a mutual
          non-disclosure agreement and a data addendum also govern handling. A Data Processing
          Addendum is available on request for business customers; email{" "}
          <a className="text-teal underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>.
        </p>
      </Section>

      <Section id="transfers" title="International data transfers">
        <p>
          Our hosting and database vendors are headquartered in the United States, and
          data is stored there. If you are in the EU/EEA, the UK or Switzerland, we
          agree the transfer mechanism with you in the data addendum before you send
          any files. Ask us for the current position at any time.
        </p>
      </Section>

      <Section id="cookies" title="Cookies">
        <p>
          We use two functional cookies, both strictly necessary to operate
          the Service: <code>pk_lead</code> (remembers that you
          submitted the lead form for the sample) and <code>pk_access</code>{" "}
          (remembers that you have entered a valid access code for your own
          data). We do not use advertising, retargeting, or cross-site
          tracking cookies. When enabled, our analytics set no cookies at all.
        </p>
        <p>
          Vercel Web Analytics can be enabled as a cookieless,
          privacy-preserving first-party analytics service. It aggregates page
          views without cross-site tracking or advertising cookies. When it is
          not enabled for the deployment, Pricekeel does not load its script.
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
            <span className="font-medium text-fg">Files sent for an audit:</span>{" "}
            deleted within 30 days of the engagement ending, with written
            confirmation.
          </li>
          <li>
            <span className="font-medium text-fg">Server logs:</span> 30 days.
          </li>
        </ul>
      </Section>

      <Section id="security" title="Security measures (GDPR Art. 32)">
        <p>
          Encryption in transit (TLS 1.2+) on all endpoints. Encryption at rest on the
          database (AES-256 via Neon). Secrets stored in encrypted environment-variable
          stores. Database access from the server only; no database credential in the
          browser. Multi-factor authentication on every admin account. We are not SOC 2
          certified. See the{" "}
          <a className="text-teal underline" href="/trust">Trust page</a>.
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
