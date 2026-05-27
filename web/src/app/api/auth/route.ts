import { cookies } from "next/headers";
import { ACCESS_COOKIE, accessToken } from "@/lib/auth";
import { isValidAccessCode } from "@/lib/store";

// POST { code } -> set the access cookie if the code is valid (unlocks /upload).
export async function POST(req: Request) {
  let code = "";
  try {
    ({ code } = await req.json());
  } catch {
    return Response.json({ error: "Bad request" }, { status: 400 });
  }
  if (!code || !(await isValidAccessCode(code))) {
    return Response.json({ error: "That access code is not valid." }, { status: 401 });
  }
  (await cookies()).set(ACCESS_COOKIE, await accessToken(), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
    maxAge: 60 * 60 * 24 * 7, // one week
  });
  return Response.json({ ok: true });
}

export async function DELETE() {
  (await cookies()).delete(ACCESS_COOKIE);
  return Response.json({ ok: true });
}
