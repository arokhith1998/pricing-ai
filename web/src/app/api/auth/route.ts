import { cookies } from "next/headers";
import { AUTH_COOKIE, authEnabled, expectedToken, isValidCode } from "@/lib/auth";

// POST { code } -> set the auth cookie if the code is right.
export async function POST(req: Request) {
  if (!authEnabled()) return Response.json({ ok: true });

  let code = "";
  try {
    ({ code } = await req.json());
  } catch {
    return Response.json({ error: "Bad request" }, { status: 400 });
  }
  if (!isValidCode(code)) {
    return Response.json({ error: "That access code is not right." }, { status: 401 });
  }

  (await cookies()).set(AUTH_COOKIE, await expectedToken(), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
    maxAge: 60 * 60 * 24 * 7, // one week
  });
  return Response.json({ ok: true });
}

// DELETE -> sign out.
export async function DELETE() {
  (await cookies()).delete(AUTH_COOKIE);
  return Response.json({ ok: true });
}
