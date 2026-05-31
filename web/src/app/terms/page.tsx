import type { Metadata } from "next";

export const metadata: Metadata = { title: "Terms of Use · Pricekeel" };

// NOTE TO FOUNDER: this is a DRAFT Terms of Use written to provide working
// language for counsel to mark up. It is NOT legal advice and is not a final
// instrument. Fill the [bracketed] entity/jurisdiction fields and have a
// lawyer review before relying on it. The effective date is a placeholder.

const EFFECTIVE = "30 May 2026";
const CONTACT = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "[legal@pricekeel.com]";

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
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-3xl font-bold text-fg">Terms of Use</h1>
      <p className="mt-2 text-sm text-muted">
        Effective {EFFECTIVE} ·{" "}
        <span className="inline-block rounded border border-coral/40 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-coral">
          DRAFT, counsel review pending
        </span>
      </p>

      <p className="mt-6 text-sm leading-relaxed text-muted">
        These Terms of Use (the &ldquo;Terms&rdquo;) govern your access to and
        use of the Pricekeel website at{" "}
        <span className="text-fg">pricekeel.com</span> and the diagnostic,
        guidance, copilot, and competitor-watch features made available there
        (collectively, the &ldquo;Service&rdquo;). Pricekeel is operated by{" "}
        <span className="text-fg">[legal entity]</span>, a{" "}
        <span className="text-fg">[jurisdiction]</span> company
        (&ldquo;Pricekeel&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;). By
        using the Service, you agree to these Terms. If you do not agree, do
        not use the Service.
      </p>

      <Section id="account" title="1. Acceptance and account">
        <p>
          You must be at least 16 years old to use the Service and authorized
          to bind your employer if you are accessing the Service on behalf of
          a company. By submitting the lead form, using a Pricekeel-issued
          access code, or uploading data to the Service, you accept these
          Terms.
        </p>
      </Section>

      <Section id="license" title="2. License grant">
        <p>
          Subject to your compliance with these Terms, Pricekeel grants you a
          limited, non-exclusive, non-transferable, revocable license to use
          the Service for your internal business purposes. You may not resell
          the Service, sublicense it, or expose it as a service to third
          parties without our prior written consent.
        </p>
      </Section>

      <Section id="customer-data" title="3. Customer data">
        <p>
          <span className="font-medium text-fg">You own your data.</span> The
          deal data, documents, pricing URLs, and other inputs you provide
          (&ldquo;Customer Data&rdquo;) remain your property. You grant
          Pricekeel a non-exclusive, worldwide license to process the Customer
          Data solely to provide the Service to you, to generate the analyses
          you request, and to maintain and improve the Service in
          aggregate-only form (for example, performance metrics).
        </p>
        <p>
          Pricekeel does not use Customer Data to train any model and does not
          sell or share Customer Data with third parties for their own
          purposes, except subprocessors necessary to provide the Service
          (listed at <a className="text-teal underline" href="/subprocessors">/subprocessors</a>).
        </p>
        <p>
          Row-level deal data uploaded to the diagnostic is processed in
          memory and not persisted after the analysis completes.
        </p>
      </Section>

      <Section id="ai-outputs" title="4. AI outputs">
        <p>
          The Service uses third-party AI providers to generate written
          narratives, column-mapping suggestions, structured plan extractions,
          and copilot answers. As between you and Pricekeel, you own the
          outputs derived from your Customer Data. AI outputs are
          probabilistic and may contain errors or omissions; you remain
          responsible for any business decision you make based on them.
        </p>
      </Section>

      <Section id="prohibited" title="5. Prohibited uses">
        <p>You agree not to:</p>
        <ul className="list-disc space-y-1 pl-6">
          <li>upload Customer Data you do not own or are not authorized to share;</li>
          <li>
            use the Competitor Watch feature against URLs you do not have the
            right to query under the operator&rsquo;s terms (you warrant you
            have such right for any URL you submit);
          </li>
          <li>
            attempt to reverse-engineer the Service, decompile its models, or
            scrape the Service&rsquo;s outputs to train a competing model;
          </li>
          <li>
            use the Service to violate any law, infringe intellectual
            property, or harm a third party;
          </li>
          <li>
            interfere with the Service&rsquo;s operation, probe for
            vulnerabilities without prior written permission, or attempt
            unauthorized access;
          </li>
          <li>resell or sublicense the Service.</li>
        </ul>
      </Section>

      <Section id="confidentiality" title="6. Confidentiality">
        <p>
          Each party will protect the other&rsquo;s non-public information
          received under these Terms with the same care it uses for its own
          confidential information, and at least reasonable care. Customer
          Data is your confidential information.
        </p>
      </Section>

      <Section id="warranty" title="7. Disclaimers (AS-IS)">
        <p>
          THE FREE TIER OF THE SERVICE (INCLUDING THE BUNDLED SAMPLE
          DIAGNOSTIC, THE DEMO COPILOT, AND THE COMPETITOR WATCH PREVIEW) IS
          PROVIDED &ldquo;AS IS&rdquo; WITHOUT WARRANTIES OF ANY KIND,
          EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION ANY WARRANTY OF
          MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, ACCURACY, OR
          NON-INFRINGEMENT. PAID ENGAGEMENTS ARE GOVERNED BY THE
          ADDITIONAL TERMS IN A SIGNED ORDER FORM OR MSA.
        </p>
      </Section>

      <Section id="liability" title="8. Limitation of liability">
        <p>
          TO THE MAXIMUM EXTENT PERMITTED BY LAW, PRICEKEEL&rsquo;S TOTAL
          AGGREGATE LIABILITY ARISING OUT OF OR RELATED TO THESE TERMS WILL
          NOT EXCEED, IN AGGREGATE, THE FEES YOU PAID TO PRICEKEEL IN THE
          TWELVE (12) MONTHS BEFORE THE EVENT GIVING RISE TO THE CLAIM, OR,
          FOR FREE-TIER USE, ONE HUNDRED U.S. DOLLARS ($100). NEITHER PARTY
          WILL BE LIABLE FOR INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR
          PUNITIVE DAMAGES.
        </p>
      </Section>

      <Section id="indemnity" title="9. Indemnification">
        <p>
          You will indemnify and hold Pricekeel harmless from any third-party
          claim arising out of (a) your Customer Data, including any claim
          that the upload, use, or content of Customer Data infringes
          third-party rights, and (b) your use of the Service in violation of
          these Terms.
        </p>
      </Section>

      <Section id="termination" title="10. Termination">
        <p>
          Either party may terminate these Terms at any time on notice.
          Pricekeel may suspend or terminate access immediately for any
          material violation of these Terms or for any conduct that risks
          harm to Pricekeel or other users. Sections that by their nature
          should survive termination (data ownership, disclaimers,
          limitation of liability, indemnification) survive.
        </p>
      </Section>

      <Section id="governing-law" title="11. Governing law and venue">
        <p>
          These Terms are governed by the laws of{" "}
          <span className="text-fg">[Delaware, USA]</span> (or such other
          jurisdiction named in a signed order form). The parties submit to
          the exclusive jurisdiction of the courts located in{" "}
          <span className="text-fg">[New Castle County, Delaware]</span>,
          subject to either party&rsquo;s right to seek injunctive relief in
          any court of competent jurisdiction.
        </p>
      </Section>

      <Section id="changes" title="12. Changes to the Terms">
        <p>
          We may update these Terms from time to time. Material changes will
          be posted here with an updated effective date; for paid customers,
          we will also provide notice in-product or by email. Your continued
          use of the Service after a change becomes effective constitutes
          acceptance of the change.
        </p>
      </Section>

      <Section id="contact" title="13. Contact">
        <p>
          Questions about these Terms? Email{" "}
          <a className="text-teal underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>.
        </p>
      </Section>
    </main>
  );
}
