import { cookies } from "next/headers";
import {
  ACCESS_COOKIE,
  accessCookieOptions,
  makeAccessCookieValue,
} from "@/lib/auth";
import { isValidAccessCode } from "@/lib/store";
import { rateLimit } from "@/lib/ratelimit";

// POST { code } -> set the access cookie if the code is valid (unlocks /upload).
// The cookie is HMAC-signed and embeds the code, so each customer's cookie is
// distinct and revoking a code in access_codes revokes that customer.
export async function POST(req: Request) {
  const limited = rateLimit(req, "auth", { max: 5, windowMs: 60_000 });
  if (limited) return limited;

  let code = "";
  try {
    ({ code } = await req.json());
  } catch {
    return Response.json({ error: "Bad request" }, { status: 400 });
  }
  if (!code || !(await isValidAccessCode(code))) {
    return Response.json({ error: "That access code is not valid." }, { status: 401 });
  }
  (await cookies()).set(
    ACCESS_COOKIE,
    await makeAccessCookieValue(code),
    accessCookieOptions(),
  );
  return Response.json({ ok: true });
}

export async function DELETE() {
  (await cookies()).delete(ACCESS_COOKIE);
  return Response.json({ ok: true });
}
