import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacy Policy · Pricekeel" };

// NOTE TO FOUNDER: this is an accurate description of what the app does today,
// but it is NOT legal advice and is not a substitute for review by counsel.
// Fill the [bracketed] entity/jurisdiction/contact fields and have a lawyer
// review before relying on it. Effective date below is a placeholder.

const EFFECTIVE = "27 May 2026";
const CONTACT = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "[privacy@yourdomain.com]";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-8">
      <h2 className="text-lg font-semibold text-fg">{title}</h2>
      <div className="mt-2 space-y-3 text-sm leading-relaxed text-muted">{children}</div>
    </section>
  );
}

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-3xl font-bold text-fg">Privacy Policy</h1>
      <p className="mt-2 text-sm text-muted">Effective {EFFECTIVE}</p>

      <p className="mt-6 text-sm leading-relaxed text-muted">
        This policy explains what Pricekeel (&ldquo;we&rdquo;, operated by
        [legal entity], [jurisdiction]) collects, why, and what we do with it. We
        keep data collection to the minimum needed to run the product.
      </p>

      <Section title="What we collect">
        <p>
          <span className="font-medium text-fg">Contact details you give us.</span>{" "}
          When you request the full sample, we collect your name, company, job
          title, role function, and company email address.
        </p>
        <p>
          <span className="font-medium text-fg">Data you upload for analysis.</span>{" "}
          When you run the diagnostic on your own CSV, that file is processed in
          memory to compute your results and is then deleted. We do not store
          your uploaded deal data, and we do not use it to train any model.
        </p>
        <p>
          <span className="font-medium text-fg">Access codes.</span> If you are
          issued an access code, we record it and when it is used.
        </p>
        <p>
          <span className="font-medium text-fg">Basic technical logs.</span>{" "}
          Standard server logs (e.g. IP address, timestamp) kept for security and
          reliability.
        </p>
      </Section>

      <Section title="How we use it">
        <p>
          To provide the diagnostic and guidance, to follow up with you about
          your results and the product, and to manage access. We do not sell your
          personal information, and we do not use it for third-party advertising.
        </p>
      </Section>

      <Section title="AI processing">
        <p>
          To generate the written summary and to map your CSV column names, we
          send <span className="font-medium text-fg">only aggregate figures and
          column header names</span> to our AI provider (OpenAI or Anthropic) —
          never row-level deal data. This is done under the provider&rsquo;s
          zero-retention / data-processing terms.
        </p>
      </Section>

      <Section title="Who we share it with">
        <p>
          Service providers that run the product on our behalf: our hosting
          provider, our database provider (for leads and access codes), and the
          AI provider described above. They process data only to provide their
          service to us. For uploaded deal data shared during an engagement, a
          mutual NDA governs handling.
        </p>
      </Section>

      <Section title="Cookies">
        <p>
          We use a small number of functional cookies to remember that you have
          unlocked the sample (<code>pk_lead</code>) or entered a valid access
          code (<code>pk_access</code>). We do not use advertising or
          cross-site tracking cookies.
        </p>
      </Section>

      <Section title="Retention">
        <p>
          We keep your contact details until you ask us to delete them. Uploaded
          deal files are not retained beyond the moment of analysis.
        </p>
      </Section>

      <Section title="Your rights">
        <p>
          Depending on where you live (for example under GDPR or CCPA), you may
          have the right to access, correct, or delete your personal information,
          or to object to its processing. To exercise these rights, contact us at{" "}
          <a className="text-teal underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>.
        </p>
      </Section>

      <Section title="Changes & contact">
        <p>
          We will post any changes to this policy here with an updated effective
          date. Questions? Email{" "}
          <a className="text-teal underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>.
        </p>
      </Section>
    </main>
  );
}
