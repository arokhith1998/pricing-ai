import { cookies } from "next/headers";
import { LEAD_COOKIE, isCompanyEmail } from "@/lib/auth";
import { saveLead } from "@/lib/store";

// POST a lead -> store it -> set pk_lead, which unlocks the full sample.
export async function POST(req: Request) {
  let body: Record<string, string>;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "Bad request" }, { status: 400 });
  }

  const name = (body.name ?? "").trim();
  const company = (body.company ?? "").trim();
  const email = (body.email ?? "").trim();
  const role_title = (body.role_title ?? "").trim();
  const role_function = (body.role_function ?? "").trim();

  if (!name || !company || !email || !role_title || !role_function) {
    return Response.json({ error: "Please fill in every field." }, { status: 400 });
  }
  if (!isCompanyEmail(email)) {
    return Response.json(
      { error: "Please use your company email address (not a personal one)." },
      { status: 400 },
    );
  }

  try {
    await saveLead({ name, company, email, role_title, role_function });
  } catch {
    return Response.json({ error: "Could not save right now. Try again." }, { status: 500 });
  }

  (await cookies()).set(LEAD_COOKIE, "1", {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
    maxAge: 60 * 60 * 24 * 30, // 30 days
  });
  return Response.json({ ok: true });
}
