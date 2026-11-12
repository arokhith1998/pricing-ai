import Link from "next/link";
import { PageHeader, Section } from "@/components/ui";
import { pageMetadata } from "@/lib/page-metadata";

// PK-116 (F17): this page says what is true today and nothing more. Update it
// when a control lands, a vendor changes, or the engagement terms change.
export const dynamic = "force-static";
export const metadata = pageMetadata({
  title: "Trust",
  description:
    "How Pricekeel handles your files: a mutual NDA first, exports only, used only for your audit, deleted within 30 days, and not SOC 2 certified.",
  path: "/trust",
});

const EFFECTIVE = "11 November 2026";
const CONTACT = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "adhithya@pricekeel.com";

const TRUST_STATEMENTS: string[] = [
  "Pricekeel is run by one founder. We accept no customer files until a mutual NDA and data addendum are signed.",
  "We work only from exports you send: no API keys, no system connections, no end-user personal data.",
  "Files are used only to deliver your audit. They are not used to improve models that benefit other customers without your written consent.",
  "We delete them within 30 days of the engagement ending and confirm it in writing.",
  "We are not SOC 2 certified.",
];

export default function TrustPage() {
  return (
    <main id="main" tabIndex={-1} className="outline-none">
      <Section width="prose">
        <PageHeader title="Trust" lead={`Updated ${EFFECTIVE}.`} />
        <ul className="pk-body m-0 mt-6 list-disc space-y-3 pl-5 text-muted marker:text-teal">
          {TRUST_STATEMENTS.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
        <p className="pk-body mt-4 text-muted">
          Ask{" "}
          <a className="text-teal underline" href={`mailto:${CONTACT}`}>
            {CONTACT}
          </a>{" "}
          anything specific.
        </p>

        <h2 className="pk-h3 m-0 mt-10">Where the website runs</h2>
        <p className="pk-body mt-3 text-muted">
          This website is hosted on Vercel in the United States. If you send a message through a form
          on the site, it is stored in a Neon Postgres database in the United States. Connections use
          TLS, and Neon encrypts the database at rest. Our vendors are listed on the{" "}
          <Link className="text-teal underline" href="/subprocessors">
            subprocessors page
          </Link>
          . How we handle personal data on this website is in the{" "}
          <Link className="text-teal underline" href="/privacy">
            privacy policy
          </Link>
          .
        </p>

        <h2 className="pk-h3 m-0 mt-10">Reporting a vulnerability</h2>
        <p className="pk-body mt-3 text-muted">
          If you believe you have found a security problem, email{" "}
          <a className="text-teal underline" href={`mailto:${CONTACT}`}>
            {CONTACT}
          </a>{" "}
          rather than disclosing it publicly. We will acknowledge within two business days. We do not
          offer a paid bug bounty.
        </p>
      </Section>
    </main>
  );
}
