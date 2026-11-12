import type { Metadata } from "next";

// The layout title template adds "· Pricekeel", so the title here is bare.
export const metadata: Metadata = { title: "Terms of Use" };

// NOTE TO FOUNDER: these are short website terms, not a final instrument and
// not legal advice. We do not name a legal entity, a jurisdiction or a
// governing law here; the engagement letter carries them. Have a lawyer review
// before relying on this page.

const EFFECTIVE = "11 November 2026";
const CONTACT = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "adhithya@pricekeel.com";

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="mt-8">
      <h2 className="text-lg font-semibold text-fg">{title}</h2>
      <div className="mt-2 space-y-3 text-sm leading-relaxed text-muted">{children}</div>
    </section>
  );
}

export default function TermsPage() {
  return (
    <main id="main" tabIndex={-1} className="mx-auto max-w-3xl px-6 py-12 outline-none">
      <h1 className="text-3xl font-bold text-fg">Terms of Use</h1>
      <p className="mt-2 text-sm text-muted">
        Last updated {EFFECTIVE}. Under legal review. Questions:{" "}
        <a className="text-teal underline" href={`mailto:${CONTACT}`}>
          {CONTACT}
        </a>
      </p>

      <p className="mt-6 text-sm leading-relaxed text-muted">
        These terms cover your use of the Pricekeel website at{" "}
        <span className="text-fg">pricekeel.com</span>. By using the website you agree to them. If you do not
        agree, do not use it. A paid audit is governed by the engagement letter, a mutual NDA and a data
        addendum, which you sign before any files are sent.
      </p>

      <Section id="use" title="1. Using the website">
        <p>
          You may read the website and contact us through it for your own business purposes. You agree not to
          interfere with the website, probe it for vulnerabilities without our written permission, attempt
          unauthorized access, or use it to break the law or harm a third party.
        </p>
      </Section>

      <Section id="content" title="2. What the website says">
        <p>
          The website describes a service. It is not advice and it does not promise a result. Where the
          website shows figures, it labels them as illustrative or from a synthetic sample. Pricing decisions
          stay with you.
        </p>
      </Section>

      <Section id="files" title="3. Files you send us">
        <p>
          You send files only after the NDA and data addendum are signed. You own your files. We use them only
          to deliver your audit, and we delete them within 30 days of the engagement ending and confirm it in
          writing. The privacy policy and the trust page say more.
        </p>
      </Section>

      <Section id="warranty" title="4. Disclaimers">
        <p>
          THE WEBSITE IS PROVIDED &ldquo;AS IS&rdquo; WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED. TO THE
          MAXIMUM EXTENT PERMITTED BY LAW, WE ARE NOT LIABLE FOR INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL
          OR PUNITIVE DAMAGES ARISING FROM YOUR USE OF THE WEBSITE.
        </p>
      </Section>

      <Section id="engagement" title="5. Engagement terms">
        <p>
          Terms for a paid engagement, including the contracting entity and governing law, will be provided
          with the engagement letter.
        </p>
      </Section>

      <Section id="changes" title="6. Changes and contact">
        <p>
          We may update these terms and will post the new version here with an updated date. Questions? Email{" "}
          <a className="text-teal underline" href={`mailto:${CONTACT}`}>
            {CONTACT}
          </a>
          .
        </p>
      </Section>
    </main>
  );
}
