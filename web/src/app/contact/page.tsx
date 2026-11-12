import { Button, PageHeader, Section } from "@/components/ui";
import { pageMetadata } from "@/lib/page-metadata";
import { BOOKING_LABEL, BOOKING_URL } from "@/lib/site-nav";

// PK-116 (F17): a conversation invitation, not a request form. Under 120 words.
// pageMetadata takes the bare title; the layout template adds "· Pricekeel" once.
export const dynamic = "force-static";
export const metadata = pageMetadata({
  title: "Contact",
  description:
    "Twenty minutes on how AI founders decide what to charge per unit. A conversation, not a pitch. No data, no access, no preparation.",
  path: "/contact",
});

const CONTACT_EMAIL = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "adhithya@pricekeel.com";

export default function ContactPage() {
  return (
    <main id="main" tabIndex={-1} className="outline-none">
      <Section width="prose">
        <PageHeader title="Twenty minutes on how you price per unit" />
        <p className="pk-body mt-4 max-w-prose text-muted">
          I am talking to fifteen AI founders about how they decide what to charge per unit, and how
          they find which customers cost more to serve than they pay. It is a conversation, not a
          pitch. No data, no access, no preparation.
        </p>
        <div className="mt-6">
          <Button href={BOOKING_URL} size="lg">
            {BOOKING_LABEL}
          </Button>
        </div>
        <p className="pk-body mt-6 max-w-prose text-muted">
          Prefer a one-line answer? Email{" "}
          <a className="text-teal underline" href={`mailto:${CONTACT_EMAIL}`}>
            {CONTACT_EMAIL}
          </a>
          . I share what I learn, anonymised.
        </p>
      </Section>
    </main>
  );
}
