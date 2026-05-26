import { getSummary } from "@/lib/api";

// Async server component, streamed in via <Suspense> so the page paints first.
export default async function Summary() {
  let data: { enabled: boolean; summary: string | null };
  try {
    data = await getSummary();
  } catch {
    return (
      <p className="text-sm text-slate">Summary is unavailable right now.</p>
    );
  }
  if (!data.enabled || !data.summary) {
    return (
      <p className="text-sm text-slate">
        Add an API key to turn on a written summary of this diagnostic.
      </p>
    );
  }
  return <p className="leading-relaxed text-ink">{data.summary}</p>;
}
