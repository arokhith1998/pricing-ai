import type { Metadata } from "next";

export const metadata: Metadata = { title: "Subprocessors · Pricekeel" };

// NOTE TO FOUNDER: this list reflects the actual processors in production
// as of the date below. Update when you change a hosting vendor, LLM
// provider, or email host. Counsel should confirm the DPA links and the
// transfer mechanism descriptions.

const EFFECTIVE = "30 May 2026";
const CONTACT = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "[privacy@pricekeel.com]";

type Sub = {
  name: string;
  purpose: string;
  region: string;
  dataCategory: string;
  dpa: string;
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
    dpa: "https://render.com/legal/dpa",
  },
  {
    name: "Supabase",
    purpose: "Postgres database (leads, access codes)",
    region: "United States (us-east-1)",
    dataCategory: "Lead contact details, access codes",
    dpa: "https://supabase.com/legal/dpa",
  },
  {
    name: "OpenAI",
    purpose:
      "LLM provider — narrative summaries, column-mapper fallback, copilot answers, plan extraction",
    region: "United States",
    dataCategory:
      "Aggregate analysis figures, column header names, uploaded document chunks, user questions, public pricing-page text",
    dpa: "https://openai.com/policies/data-processing-addendum",
  },
  {
    name: "Perplexity",
    purpose: "Web search (only when explicitly enabled by user in copilot)",
    region: "United States",
    dataCategory: "User question text only",
    dpa: "https://www.perplexity.ai/hub/legal/data-processing-addendum",
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
    dpa: "https://www.godaddy.com/legal/agreements/data-processing-addendum",
  },
];

export default function SubprocessorsPage() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-3xl font-bold text-fg">Subprocessors</h1>
      <p className="mt-2 text-sm text-muted">Updated {EFFECTIVE}</p>

      <p className="mt-6 text-sm leading-relaxed text-muted">
        Pricekeel uses a small set of third-party services to operate. Each
        is bound by a written data-processing addendum (DPA) and processes
        data only on Pricekeel&rsquo;s instructions. We do not allow any
        subprocessor to use Pricekeel data for its own purposes (including
        training models on it).
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
                    DPA
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
          are <em>not</em> Pricekeel subprocessors — they are third-party
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
