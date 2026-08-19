import "server-only";

import {
  HUBSPOT_API_BASE,
  hubspotExpiryIso,
  refreshHubspotToken,
} from "@/lib/hubspot-oauth";
import {
  deleteHubspotConnection,
  getHubspotConnection,
  markHubspotConnection,
  updateHubspotTokens,
  type HubspotConnection,
} from "@/lib/hubspot-store";

// Only these prefixes are reachable through this client. HubSpot's API base is
// a single shared host, so unlike the Salesforce instance-origin check the
// meaningful guard is on the path: a continuation URL or a mapped field must
// never be able to steer a request at an unrelated HubSpot endpoint.
const ALLOWED_PATH_PREFIXES = ["/crm/v3/", "/oauth/v1/"];

// One retry only. HubSpot allows 100-190 requests per 10 seconds depending on
// tier, so a burst is recoverable, but an unbounded retry loop against a rate
// limiter is how you turn a slow sync into an outage.
const MAX_RATE_LIMIT_RETRIES = 1;
const MAX_RETRY_DELAY_MS = 10_000;
// Refresh this far ahead of expiry so a request never races the 30-minute
// access-token lifetime.
const REFRESH_SKEW_MS = 60_000;

export function hubspotTarget(path: string): URL {
  const target = new URL(path, HUBSPOT_API_BASE);
  if (
    target.origin !== HUBSPOT_API_BASE ||
    !ALLOWED_PATH_PREFIXES.some((prefix) => target.pathname.startsWith(prefix))
  ) {
    throw new Error("Blocked an invalid HubSpot API URL.");
  }
  return target;
}

function expiresSoon(connection: HubspotConnection): boolean {
  if (!connection.issued_at) return false;
  const expiry = Date.parse(connection.issued_at);
  if (!Number.isFinite(expiry)) return false;
  return expiry - REFRESH_SKEW_MS <= Date.now();
}

async function refreshConnection(
  customerRef: string,
  connection: HubspotConnection,
): Promise<HubspotConnection> {
  let token;
  try {
    token = await refreshHubspotToken(connection.refresh_token);
  } catch (error) {
    await markHubspotConnection(
      customerRef,
      "reauth_required",
      error instanceof Error ? error.message : "Refresh failed.",
    );
    throw new Error("HubSpot authorization expired. Reconnect the portal.");
  }
  await updateHubspotTokens(customerRef, {
    access_token: token.access_token,
    refresh_token: token.refresh_token,
    token_type: token.token_type,
    issued_at: hubspotExpiryIso(token),
  });
  const updated = await getHubspotConnection(customerRef);
  if (!updated) throw new Error("HubSpot connection disappeared after refresh.");
  return updated;
}

function retryDelayMs(response: Response): number {
  const header = response.headers.get("Retry-After");
  const seconds = header ? Number(header) : NaN;
  if (Number.isFinite(seconds) && seconds > 0) {
    return Math.min(seconds * 1000, MAX_RETRY_DELAY_MS);
  }
  return 1000;
}

export async function hubspotApiRequest(
  customerRef: string,
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  let connection = await getHubspotConnection(customerRef);
  if (!connection) throw new Error("Connect HubSpot before syncing.");
  if (expiresSoon(connection)) {
    connection = await refreshConnection(customerRef, connection);
  }

  const run = (current: HubspotConnection) =>
    fetch(hubspotTarget(path), {
      ...init,
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${current.access_token}`,
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...(init.headers ?? {}),
      },
      cache: "no-store",
    });

  let response = await run(connection);
  let refreshed = false;
  if (response.status === 401) {
    connection = await refreshConnection(customerRef, connection);
    response = await run(connection);
    refreshed = true;
  }
  for (
    let attempt = 0;
    response.status === 429 && attempt < MAX_RATE_LIMIT_RETRIES;
    attempt += 1
  ) {
    await new Promise((resolve) => setTimeout(resolve, retryDelayMs(response)));
    response = await run(connection);
  }

  if (!response.ok) {
    const code = response.status;
    const raw = await response.text().catch(() => "");
    let detail = "";
    try {
      const parsed = JSON.parse(raw) as { message?: string; category?: string };
      detail = [parsed?.category, parsed?.message].filter(Boolean).join(": ");
    } catch {
      detail = raw.trim();
    }
    const safeDetail = detail.replace(/[\r\n]+/g, " ").slice(0, 500);
    const message = `HubSpot API request failed (${code})${safeDetail ? `: ${safeDetail}` : "."}`;
    const status = code === 401 && refreshed ? "reauth_required" : "error";
    await markHubspotConnection(customerRef, status, message);
    if (status === "reauth_required") {
      throw new Error(
        "HubSpot authorization was rejected after refresh. Reconnect the portal.",
      );
    }
    throw new Error(message);
  }
  if (connection.status !== "connected") {
    await markHubspotConnection(customerRef, "connected", "");
  }
  return response;
}

export async function disconnectHubspot(customerRef: string): Promise<void> {
  const connection = await getHubspotConnection(customerRef);
  if (connection?.refresh_token) {
    // Best effort. A failed revoke must not block the local delete, or a
    // customer who asks to disconnect stays connected in our database.
    try {
      await fetch(
        `${HUBSPOT_API_BASE}/oauth/v1/refresh-tokens/${encodeURIComponent(
          connection.refresh_token,
        )}`,
        { method: "DELETE", cache: "no-store" },
      );
    } catch {
      // Swallowed on purpose; see above.
    }
  }
  await deleteHubspotConnection(customerRef);
}
