import { getRecommendation } from "@/lib/api";

// Same-origin proxy to the FastAPI /recommend endpoint. Keeps the API base URL
// server-side (PRICEKEEL_API), so the browser only ever talks to this origin.
export async function POST(req: Request) {
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
    const rec = await getRecommendation(opportunity_id);
    return Response.json(rec);
  } catch {
    return Response.json({ error: "Guidance is unavailable" }, { status: 502 });
  }
}
