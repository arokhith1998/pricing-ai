// Same-origin proxy: forward document uploads to FastAPI /docs/upload.
import { requireAccess } from "@/lib/gate";

const API = process.env.PRICEKEEL_API ?? "http://127.0.0.1:8000";

export async function POST(req: Request) {
  // Doc parsing runs on the caller's files — access-code tier.
  const denied = await requireAccess();
  if (denied) return denied;

  let form: FormData;
  try {
    form = await req.formData();
  } catch {
    return Response.json({ error: "Expected a file upload." }, { status: 400 });
  }
  try {
    const upstream = await fetch(`${API}/docs/upload`, { method: "POST", body: form });
    if (!upstream.ok) {
      const text = await upstream.text().catch(() => "");
      return Response.json({ error: text || "Could not parse those docs." }, { status: 502 });
    }
    return Response.json(await upstream.json());
  } catch {
    return Response.json({ error: "Document service is unavailable." }, { status: 502 });
  }
}
