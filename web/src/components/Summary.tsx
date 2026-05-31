import { getSummary } from "@/lib/api";
import { renderMarkdown } from "@/lib/markdown";

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
  // The LLM returns markdown (bolds, numbered lists). Render it. Plain text
  // shows the raw asterisks, which reads as a broken AI output.
  return (
    <div
      className="pk-prose leading-relaxed text-ink"
      dangerouslySetInnerHTML={{ __html: renderMarkdown(data.summary) }}
    />
  );
}
