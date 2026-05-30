// Cookie gates for /api/* route handlers.
//
// The Next.js proxy only redirects user-facing /pages — same-origin /api/*
// routes (which proxy uploads + LLM calls to FastAPI) need their own check
// or anyone who knows the URL can call them from curl/Postman.
//
// Use one of these at the top of a route handler:
//
//   const denied = await requireLead();
//   if (denied) return denied;
//
//   const denied = await requireAccess();
//   if (denied) return denied;
//
// requireLead unlocks the demo/sample-backed endpoints (recommend, copilot,
// matching, ask). requireAccess unlocks endpoints that operate on the user's
// own uploaded files (diagnostic, docs, map-headers).

import { cookies } from "next/headers";
import { ACCESS_COOKIE, LEAD_COOKIE, accessToken } from "@/lib/auth";

export async function requireLead(): Promise<Response | null> {
  const has = (await cookies()).get(LEAD_COOKIE)?.value;
  if (has) return null;
  return Response.json(
    { error: "Lead capture required. Unlock the sample at /sample." },
    { status: 401 },
  );
}

export async function requireAccess(): Promise<Response | null> {
  const token = (await cookies()).get(ACCESS_COOKIE)?.value;
  if (token && token === (await accessToken())) return null;
  return Response.json(
    { error: "Access code required. Sign in at /login." },
    { status: 401 },
  );
}
