// Same-origin proxy: forward an uploaded CSV to the FastAPI /diagnostic
// endpoint. Keeps the API URL server-side; the API deletes the file after use.
const API = process.env.PRICEKEEL_API ?? "http://127.0.0.1:8000";

export async function POST(req: Request) {
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
    const upstream = await fetch(`${API}/diagnostic`, { method: "POST", body: form });
    if (!upstream.ok) {
      return Response.json(
        { error: "Could not analyze that file. Check it against the template." },
        { status: 502 },
      );
    }
    return Response.json(await upstream.json());
  } catch {
    return Response.json({ error: "The analysis service is unavailable." }, { status: 502 });
  }
}
