import UploadClient from "@/components/UploadClient";

export const dynamic = "force-dynamic";

const REQUIRED = [
  ["opportunity_id", "Unique opportunity id (one row per opportunity)"],
  ["account_name", "Customer account name (may be messy / inconsistent)"],
  ["outcome", "closed_won or closed_lost"],
  ["created_date", "When the opportunity was created"],
  ["close_date", "When it closed (drives quarter-end analysis)"],
  ["segment", "SMB | MidMarket | Enterprise"],
  ["product_tier", "Plan / package sold"],
  ["value_metric", "seats | consumption | hybrid"],
  ["list_acv", "Annualized value at list price (pre-discount)"],
  ["booked_acv", "Annualized value actually booked (post-discount)"],
];

const OPTIONAL =
  "account_id, region, industry, platform_fee_acv, usage_acv, term_months, quantity, rep_id, approved_by, competitor_present, lost_reason";

export default function UploadPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-8 px-6 py-8">
      <div>
        <h1 className="text-2xl font-bold text-navy">Run it on your data</h1>
        <p className="mt-1 max-w-2xl text-slate">
          Export a CSV of your closed opportunities (won and lost). It is
          processed in memory to produce your diagnostic and is not stored.
        </p>
      </div>

      <section className="rounded-xl border border-mist bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-lg font-semibold text-navy">The template we expect</h2>
          <a
            href="/pricekeel-template.csv"
            download
            className="text-sm font-medium text-navy underline"
          >
            Download CSV template
          </a>
        </div>
        <p className="mt-1 text-sm text-slate">
          Ten required columns (one row per closed opportunity). The analysis
          degrades gracefully without the optional ones.
        </p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-mist text-left text-slate">
                <th className="py-2 pr-4 font-medium">Column</th>
                <th className="py-2 font-medium">What it is</th>
              </tr>
            </thead>
            <tbody>
              {REQUIRED.map(([col, desc]) => (
                <tr key={col} className="border-b border-mist/60">
                  <td className="py-2 pr-4 font-mono text-xs text-navy">{col}</td>
                  <td className="py-2 text-slate">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-slate">
          <span className="font-medium text-ink">Optional (enrich the analysis):</span>{" "}
          {OPTIONAL}
        </p>
      </section>

      <UploadClient />
    </main>
  );
}
