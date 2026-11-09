import type { Metadata } from "next";

export const metadata: Metadata = { title: "Subprocessors · Pricekeel" };

// NOTE TO FOUNDER: this list reflects the actual processors in production
// as of the date below. Update when you change a hosting vendor, LLM
// provider, or email host. Counsel should confirm the DPA links and the
// transfer mechanism descriptions.

const EFFECTIVE = "9 November 2026";
const CONTACT = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "adhithya@pricekeel.com";

type Sub = {
  name: string;
  purpose: string;
  region: string;
  dataCategory: string;
  dpa: string;
  dpaLabel?: string;
};

// Each row is what an IT-review reviewer is going to want to see in the
// first ten minutes of their evaluation. Keep accurate.
const SUBPROCESSORS: Sub[] = [
  {
    name: "Vercel",
    purpose: "Web hosting (pricekeel.com)",
    region: "United States (us-east-1) + global edge",
    dataCategory: "HTTP requests + session cookies (pk_lead, pk_access)",
    dpa: "https://vercel.com/legal/dpa",
  },
  {
    name: "Render",
    purpose: "API hosting (api.pricekeel.com)",
    region: "United States (Virginia)",
    dataCategory: "API requests, uploaded CSV (processed in memory only)",
    dpa: "https://render.com/dpa",
  },
  {
    name: "Neon",
    purpose: "Postgres database (leads, access codes, encrypted CRM tokens, mappings, decision log)",
    region: "United States (AWS us-east)",
    dataCategory: "Lead contact details, access codes, encrypted Salesforce tokens, connection metadata, logged pricing decisions",
    dpa: "https://neon.com/dpa",
    dpaLabel: "DPA (Neon schedule to the Databricks DPA)",
  },
  {
    name: "Anthropic",
    purpose:
      "LLM provider. Narrates analysis results that Pricekeel has already computed (it never computes a figure), suggests column-header mappings, answers copilot questions, and extracts plan structure from public pricing-page text",
    region:
      "United States. Pricekeel does not pin a processing region; see the Anthropic DPA for its processing locations and subprocessors",
    dataCategory:
      "Aggregate figures, column header names, uploaded document chunks, question text, public pricing-page text. Never deal rows from CSV uploads or live Salesforce rows.",
    dpa: "https://www.anthropic.com/legal/data-processing-addendum",
  },
  {
    name: "Perplexity",
    purpose: "Web search (only when explicitly enabled by user in copilot)",
    region: "United States",
    dataCategory: "User question text only",
    dpa: "https://www.perplexity.ai/hub/legal/privacy-policy",
    dpaLabel: "Privacy notice (no DPA link found)",
  },
  {
    name: "Tavily",
    purpose: "Fallback web search (only when explicitly enabled by user in copilot and Perplexity is not configured)",
    region: "United States",
    dataCategory:
      "User question text only. No DPA found: Tavily's privacy policy says it may use query data to improve its service and refers to training its models, so avoid sensitive wording in web-search questions",
    dpa: "https://www.tavily.com/privacy",
    dpaLabel: "Privacy policy (no DPA link found)",
  },
  {
    name: "Resend",
    purpose: "Transactional email (sign-in links, internal lead notifications, digests)",
    region: "Depends on account configuration",
    dataCategory: "Recipient email address and message content",
    dpa: "https://resend.com/legal/dpa",
  },
  {
    name: "Microsoft 365 (via GoDaddy)",
    purpose: "Inbound email (adhithya@pricekeel.com)",
    region: "United States / EEA (Microsoft regional data centers)",
    dataCategory: "Email correspondence",
    dpa: "https://www.microsoft.com/licensing/docs/view/Microsoft-Products-and-Services-Data-Protection-Addendum-DPA",
  },
  {
    name: "GoDaddy",
    purpose: "Domain registration + DNS for pricekeel.com",
    region: "United States",
    dataCategory: "DNS resolution requests (no personal data)",
    dpa: "https://www.godaddy.com/legal",
    dpaLabel: "Legal agreements (no DPA link found)",
  },
];

export default function SubprocessorsPage() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-3xl font-bold text-fg">Subprocessors</h1>
      <p className="mt-2 text-sm text-muted">Updated {EFFECTIVE}</p>

      <p className="mt-6 text-sm leading-relaxed text-muted">
        Pricekeel uses a small set of third-party services to operate. Where
        we found a vendor&rsquo;s data-processing addendum (DPA), the link
        below goes to it; otherwise the link goes to the vendor&rsquo;s
        published privacy or legal page and the label says no DPA link was
        found. Each subprocessor is
        instructed to process data only on Pricekeel&rsquo;s behalf, and we
        do not authorize any of them to train models on Pricekeel data.
        Anthropic is the only LLM provider that narrates or maps your
        analysis. The optional web-search services (Perplexity Sonar and
        Tavily) receive question text only, and only when you turn web
        search on.
      </p>

      <p className="mt-3 text-sm leading-relaxed text-muted">
        All subprocessors are headquartered in the United States. Where
        personal data of EU/EEA or UK individuals is transferred to the
        United States, the transfer relies on the European Commission&rsquo;s
        Standard Contractual Clauses (SCCs) referenced in the relevant DPA,
        and the EU-U.S. Data Privacy Framework where the recipient is
        certified.
      </p>

      <div className="mt-8 overflow-x-auto rounded-xl border border-mist">
        <table className="w-full border-collapse text-sm">
          <thead className="bg-surface-2 text-left text-xs uppercase tracking-wider text-muted">
            <tr>
              <th className="px-3 py-2 font-semibold">Subprocessor</th>
              <th className="px-3 py-2 font-semibold">Purpose</th>
              <th className="px-3 py-2 font-semibold">Region</th>
              <th className="px-3 py-2 font-semibold">Data category</th>
              <th className="px-3 py-2 font-semibold">DPA</th>
            </tr>
          </thead>
          <tbody>
            {SUBPROCESSORS.map((s) => (
              <tr key={s.name} className="border-t border-mist align-top">
                <td className="px-3 py-2 font-semibold text-fg">{s.name}</td>
                <td className="px-3 py-2 text-ink">{s.purpose}</td>
                <td className="px-3 py-2 text-muted">{s.region}</td>
                <td className="px-3 py-2 text-muted">{s.dataCategory}</td>
                <td className="px-3 py-2">
                  <a
                    className="text-teal underline"
                    href={s.dpa}
                    target="_blank"
                    rel="noreferrer noopener"
                  >
                    {s.dpaLabel ?? "DPA"}
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <section className="mt-10 space-y-3 text-sm leading-relaxed text-muted">
        <h2 className="text-lg font-semibold text-fg">
          Customer pricing-page hosts
        </h2>
        <p>
          When you use the Competitor Watch feature, Pricekeel fetches the
          competitor pricing URLs you enter. The operators of those pages
          are <em>not</em> Pricekeel subprocessors; they are third-party
          publishers from whom Pricekeel retrieves publicly accessible
          content on your behalf. Pricekeel honors <code>robots.txt</code>
          and operates a kill-switch list for any host that asks us to
          stop.
        </p>
      </section>

      <section className="mt-10 space-y-3 text-sm leading-relaxed text-muted">
        <h2 className="text-lg font-semibold text-fg">Changes to this list</h2>
        <p>
          We will update this page when we add or remove a subprocessor.
          Paid customers will additionally receive notice in-product or by
          email before a new subprocessor begins processing their data, so
          they have an opportunity to object.
        </p>
      </section>

      <section className="mt-10 space-y-3 text-sm leading-relaxed text-muted">
        <h2 className="text-lg font-semibold text-fg">Contact</h2>
        <p>
          Questions about a specific subprocessor or our data-processing
          arrangements? Email{" "}
          <a className="text-teal underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>.
        </p>
      </section>
    </main>
  );
}
