// Same-origin proxy: forward an uploaded file to FastAPI /map-headers and
// return its mapping suggestion. Only the file (which never leaves the server)
// and column-name strings are processed; row data is not sent externally
// beyond what /map-headers itself sends (and that is header strings only).
import { requireAccess } from "@/lib/gate";

const API = process.env.PRICEKEEL_API ?? "http://127.0.0.1:8000";

export async function POST(req: Request) {
  // Header-mapping accepts an uploaded file — same access tier as /upload.
  const denied = await requireAccess();
  if (denied) return denied;

  let form: FormData;
  try {
    form = await req.formData();
  } catch {
    return Response.json({ error: "Expected a file upload." }, { status: 400 });
  }
  if (!form.get("file")) {
    return Response.json({ error: "No file provided." }, { status: 400 });
  }
  try {
    const upstream = await fetch(`${API}/map-headers`, { method: "POST", body: form });
    if (!upstream.ok) {
      const text = await upstream.text().catch(() => "");
      return Response.json(
        { error: text || "Could not read that file." },
        { status: 502 },
      );
    }
    return Response.json(await upstream.json());
  } catch {
    return Response.json({ error: "The mapping service is unavailable." }, { status: 502 });
  }
}
