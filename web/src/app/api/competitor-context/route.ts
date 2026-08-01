import { customerRef, requireAccess } from "@/lib/gate";
import {
  deleteCompetitorSource,
  listCompetitorSources,
  saveCompetitorSource,
  type CompetitorClaim,
} from "@/lib/competitor-store";

const API = process.env.PRICEKEEL_API ?? "http://127.0.0.1:8000";
const SOURCE_TYPES = new Set([
  "pricing",
  "documentation",
  "release_notes",
  "case_study",
  "funding",
  "executive_interview",
  "investor_material",
  "other",
]);

export const maxDuration = 60;

export async function GET() {
  const denied = await requireAccess();
  if (denied) return denied;
  try {
    return Response.json({ sources: await listCompetitorSources(await customerRef()) });
  } catch {
    return Response.json({ error: "Could not read competitor sources." }, { status: 503 });
  }
}

export async function POST(req: Request) {
  const denied = await requireAccess();
  if (denied) return denied;
  let body: { competitor_name?: unknown; source_url?: unknown; source_type?: unknown };
  try {
    body = (await req.json()) as typeof body;
  } catch {
    return Response.json({ error: "Expected a JSON source." }, { status: 400 });
  }
  const competitorName = typeof body.competitor_name === "string" ? body.competitor_name.trim() : "";
  const sourceUrl = typeof body.source_url === "string" ? body.source_url.trim() : "";
  const sourceType = typeof body.source_type === "string" ? body.source_type.trim() : "other";
  if (!competitorName || competitorName.length > 120) {
    return Response.json({ error: "Competitor name is required (120 characters maximum)." }, { status: 400 });
  }
  if (!SOURCE_TYPES.has(sourceType)) {
    return Response.json({ error: "Unsupported source type." }, { status: 400 });
  }
  try {
    const parsed = new URL(sourceUrl);
    if (parsed.protocol !== "https:" || parsed.username || parsed.password || sourceUrl.length > 2_000) {
      throw new Error();
    }
  } catch {
    return Response.json({ error: "Source URL must be a public HTTPS URL." }, { status: 400 });
  }
  const customer = await customerRef();
  try {
    const existing = await listCompetitorSources(customer);
    const names = new Set(existing.map((source) => source.competitor_name.toLowerCase()));
    if (!names.has(competitorName.toLowerCase()) && names.size >= 10) {
      return Response.json({ error: "V1 supports up to 10 named competitors." }, { status: 400 });
    }
    const upstream = await fetch(`${API}/matching/context`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Pricekeel-Key": process.env.PRICEKEEL_API_KEY ?? "",
      },
      body: JSON.stringify({
        competitor_name: competitorName,
        url: sourceUrl,
        source_type: sourceType,
      }),
      cache: "no-store",
    });
    const extracted = (await upstream.json().catch(() => ({}))) as {
      detail?: string;
      summary?: string;
      confidence?: "high" | "medium" | "low";
      claims?: CompetitorClaim[];
    };
    if (!upstream.ok) {
      return Response.json(
        { error: extracted.detail || "Could not verify that public source." },
        { status: upstream.status === 403 ? 403 : 502 },
      );
    }
    const saved = await saveCompetitorSource(customer, {
      competitor_name: competitorName,
      source_url: sourceUrl,
      source_type: sourceType,
      summary: String(extracted.summary ?? "").slice(0, 2_000),
      claims: Array.isArray(extracted.claims) ? extracted.claims.slice(0, 5) : [],
      confidence: extracted.confidence ?? "medium",
    });
    return Response.json({ source: saved });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "Could not add competitor context." },
      { status: 502 },
    );
  }
}

export async function DELETE(req: Request) {
  const denied = await requireAccess();
  if (denied) return denied;
  const id = new URL(req.url).searchParams.get("id") ?? "";
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(id)) {
    return Response.json({ error: "A valid source id is required." }, { status: 400 });
  }
  try {
    const deleted = await deleteCompetitorSource(await customerRef(), id);
    return Response.json({ deleted });
  } catch {
    return Response.json({ error: "Could not remove the source." }, { status: 503 });
  }
}
