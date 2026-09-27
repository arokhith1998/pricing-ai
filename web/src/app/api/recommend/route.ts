import { ApiError, getRecommendation } from "@/lib/api";
import { customerRef, requireLead } from "@/lib/gate";

// Same-origin proxy to the FastAPI /recommend endpoint. Keeps the API base URL
// server-side (PRICEKEEL_API), so the browser only ever talks to this origin.
export async function POST(req: Request) {
  // /guidance is demo-gated; this is the API it calls.
  const denied = await requireLead();
  if (denied) return denied;

  let opportunity_id: string;
  try {
    ({ opportunity_id } = await req.json());
  } catch {
    return Response.json({ error: "Bad request" }, { status: 400 });
  }
  if (!opportunity_id) {
    return Response.json({ error: "opportunity_id required" }, { status: 400 });
  }
  try {
    const rec = await getRecommendation(opportunity_id, await customerRef());
    return Response.json(rec);
  } catch (err) {
    // A 4xx from the backend means it understood the request and rejected
    // it (e.g. an unknown opportunity_id); forward that status and message
    // instead of the generic "unavailable" one, which belongs to a real
    // outage (5xx, timeout, connection refused).
    if (err instanceof ApiError && err.isClientError) {
      return Response.json(
        { error: err.detail ?? "That deal could not be priced." },
        { status: err.status },
      );
    }
    return Response.json({ error: "Guidance is unavailable" }, { status: 502 });
  }
}
