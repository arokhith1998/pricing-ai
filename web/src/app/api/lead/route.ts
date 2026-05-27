import { cookies } from "next/headers";
import { LEAD_COOKIE, isCompanyEmail } from "@/lib/auth";
import { saveLead } from "@/lib/store";

// POST a lead -> store it -> set pk_lead, which unlocks the full sample.
export async function POST(req: Request) {
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "Bad request" }, { status: 400 });
  }

  const str = (v: unknown) => (typeof v === "string" ? v.trim() : "");
  const name = str(body.name);
  const company = str(body.company);
  const email = str(body.email);
  const role_title = str(body.role_title);
  const role_function = str(body.role_function);

  if (!name || !company || !email || !role_title || !role_function) {
    return Response.json({ error: "Please fill in every field." }, { status: 400 });
  }
  if (!isCompanyEmail(email)) {
    return Response.json(
      { error: "Please use your company email address (not a personal one)." },
      { status: 400 },
    );
  }
  if (body.consent !== true) {
    return Response.json(
      { error: "Please agree to the Privacy Policy to continue." },
      { status: 400 },
    );
  }

  try {
    await saveLead({ name, company, email, role_title, role_function, consent: true });
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
