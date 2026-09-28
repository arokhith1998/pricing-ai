import "server-only";

import {
  deleteSalesforceConnection,
  getSalesforceConnection,
  markSalesforceConnection,
  updateSalesforceTokens,
  type SalesforceConnection,
} from "@/lib/salesforce-store";
import { salesforceLoginUrl } from "@/lib/salesforce-oauth";

export type SalesforceDescribeField = {
  name: string;
  label: string;
  type: string;
  custom: boolean;
  nillable: boolean;
  calculated: boolean;
};

type QueryResponse<T> = {
  totalSize: number;
  done: boolean;
  records: T[];
  nextRecordsUrl?: string;
};

const MAX_QUERY_RECORDS = 10_000;

export function salesforceApiVersion(): string {
  const value = process.env.SALESFORCE_API_VERSION?.trim() || "67.0";
  if (!/^\d{2}\.0$/.test(value)) {
    throw new Error("SALESFORCE_API_VERSION must look like 67.0.");
  }
  return value;
}

export function validatedSalesforceOrigin(raw: string): string {
  const url = new URL(raw);
  const host = url.hostname.toLowerCase();
  if (
    url.protocol !== "https:" ||
    url.username ||
    url.password ||
    !(host === "salesforce.com" || host.endsWith(".salesforce.com"))
  ) {
    throw new Error("Salesforce returned an untrusted instance URL.");
  }
  return url.origin;
}

function salesforceClientId(): string {
  const value = process.env.SALESFORCE_CLIENT_ID?.trim();
  if (!value) throw new Error("SALESFORCE_CLIENT_ID is not configured.");
  return value;
}

function salesforceClientSecret(): string {
  const value = process.env.SALESFORCE_CLIENT_SECRET?.trim();
  if (!value) throw new Error("SALESFORCE_CLIENT_SECRET is not configured.");
  return value;
}

async function refreshConnection(
  customerRef: string,
  connection: SalesforceConnection,
): Promise<SalesforceConnection> {
  const response = await fetch(
    new URL("/services/oauth2/token", salesforceLoginUrl()),
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "refresh_token",
        refresh_token: connection.refresh_token,
        client_id: salesforceClientId(),
        client_secret: salesforceClientSecret(),
      }),
      cache: "no-store",
    },
  );
  if (!response.ok) {
    await markSalesforceConnection(
      customerRef,
      "reauth_required",
      `Refresh failed (${response.status}).`,
    );
    throw new Error("Salesforce authorization expired. Reconnect the org.");
  }
  const token = (await response.json()) as {
    access_token?: string;
    refresh_token?: string;
    instance_url?: string;
    token_type?: string;
    scope?: string;
    issued_at?: string;
  };
  if (!token.access_token) {
    await markSalesforceConnection(
      customerRef,
      "reauth_required",
      "Refresh response omitted access_token.",
    );
    throw new Error("Salesforce authorization expired. Reconnect the org.");
  }
  await updateSalesforceTokens(customerRef, {
    access_token: token.access_token,
    refresh_token: token.refresh_token,
    instance_url: token.instance_url
      ? validatedSalesforceOrigin(token.instance_url)
      : connection.instance_url,
    token_type: token.token_type,
    scope: token.scope,
    issued_at: token.issued_at,
  });
  const updated = await getSalesforceConnection(customerRef);
  if (!updated) throw new Error("Salesforce connection disappeared after refresh.");
  return updated;
}

async function apiRequest(
  customerRef: string,
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  let connection = await getSalesforceConnection(customerRef);
  if (!connection) throw new Error("Connect Salesforce before syncing.");
  const run = (current: SalesforceConnection) =>
    {
      const origin = validatedSalesforceOrigin(current.instance_url);
      const target = new URL(path, origin);
      if (target.origin !== origin || !target.pathname.startsWith("/services/data/")) {
        throw new Error("Blocked an invalid Salesforce API continuation URL.");
      }
      return fetch(target, {
      ...init,
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${current.access_token}`,
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...(init.headers ?? {}),
      },
      cache: "no-store",
      });
    };

  let response = await run(connection);
  let refreshed = false;
  if (response.status === 401) {
    connection = await refreshConnection(customerRef, connection);
    response = await run(connection);
    refreshed = true;
  }
  if (!response.ok) {
    const code = response.status;
    const raw = await response.text().catch(() => "");
    let detail = "";
    try {
      const parsed = JSON.parse(raw) as Array<{ errorCode?: string; message?: string }>;
      const first = Array.isArray(parsed) ? parsed[0] : null;
      detail = [first?.errorCode, first?.message].filter(Boolean).join(": ");
    } catch {
      detail = raw.trim();
    }
    const safeDetail = detail.replace(/[\r\n]+/g, " ").slice(0, 500);
    const message = `Salesforce API request failed (${code})${safeDetail ? `: ${safeDetail}` : "."}`;
    const status = code === 401 && refreshed ? "reauth_required" : "error";
    await markSalesforceConnection(customerRef, status, message);
    if (status === "reauth_required") {
      throw new Error("Salesforce authorization was rejected after refresh. Reconnect the org.");
    }
    throw new Error(message);
  }
  if (connection.status !== "connected") {
    await markSalesforceConnection(customerRef, "connected", "");
  }
  return response;
}

export async function describeSalesforceOpportunity(
  customerRef: string,
): Promise<SalesforceDescribeField[]> {
  const version = salesforceApiVersion();
  const response = await apiRequest(
    customerRef,
    `/services/data/v${version}/sobjects/Opportunity/describe`,
  );
  const body = (await response.json()) as { fields?: SalesforceDescribeField[] };
  return (body.fields ?? [])
    .filter((field) => field.name && field.label)
    .map((field) => ({
      name: field.name,
      label: field.label,
      type: field.type,
      custom: Boolean(field.custom),
      nillable: Boolean(field.nillable),
      calculated: Boolean(field.calculated),
    }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

export async function querySalesforce<T>(
  customerRef: string,
  soql: string,
): Promise<T[]> {
  const version = salesforceApiVersion();
  let path = `/services/data/v${version}/query?q=${encodeURIComponent(soql)}`;
  const records: T[] = [];
  while (path && records.length < MAX_QUERY_RECORDS) {
    const response = await apiRequest(customerRef, path);
    const page = (await response.json()) as QueryResponse<T>;
    records.push(...(page.records ?? []));
    path = page.done ? "" : page.nextRecordsUrl ?? "";
  }
  if (records.length >= MAX_QUERY_RECORDS) {
    throw new Error(
      `Salesforce query exceeded the ${MAX_QUERY_RECORDS.toLocaleString()} record V1 safety limit. Narrow the lookback window.`,
    );
  }
  return records;
}

export async function createSalesforceTask(
  customerRef: string,
  input: { opportunityId: string; subject: string; description: string },
): Promise<{ id: string }> {
  const version = salesforceApiVersion();
  const response = await apiRequest(
    customerRef,
    `/services/data/v${version}/sobjects/Task`,
    {
      method: "POST",
      body: JSON.stringify({
        WhatId: input.opportunityId,
        Subject: input.subject.slice(0, 255),
        Description: input.description.slice(0, 32_000),
        Status: "Completed",
        Priority: "Normal",
      }),
    },
  );
  const body = (await response.json()) as { id?: string };
  if (!body.id) throw new Error("Salesforce created the Task without returning an ID.");
  return { id: body.id };
}

export async function disconnectSalesforce(
  customerRef: string,
): Promise<{ revocationConfirmed: boolean }> {
  let connection: SalesforceConnection | null = null;
  try {
    connection = await getSalesforceConnection(customerRef);
  } catch (cause) {
    // Cannot decrypt the stored refresh token (e.g.
    // SALESFORCE_TOKEN_ENCRYPTION_KEY rotated): revocation at Salesforce is
    // impossible without it, but local deletion below only needs
    // customer_ref, not the decrypted secrets. Log the cause so this is
    // distinguishable from an ordinary revoke failure, and fall through
    // rather than leaving an undecryptable, permanently orphaned row.
    console.error(
      "[salesforce-client] disconnect: could not decrypt stored tokens; skipping the Salesforce revoke call",
      cause,
    );
  }
  // Nothing to revoke (already disconnected, or undecryptable) counts as
  // confirmed: there is no live refresh token this deletion could leave
  // behind at Salesforce.
  let revocationConfirmed = true;
  if (connection) {
    try {
      const response = await fetch(new URL("/services/oauth2/revoke", salesforceLoginUrl()), {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ token: connection.refresh_token }),
        cache: "no-store",
      });
      revocationConfirmed = response.ok;
      if (!response.ok) {
        console.error(
          `[salesforce-client] disconnect: Salesforce rejected the revoke request (status ${response.status})`,
        );
      }
    } catch (cause) {
      // Local removal is authoritative for Pricekeel: a Salesforce outage
      // must not trap a customer connection here. But the refresh token
      // stays live at Salesforce until it is revoked or expires, so this is
      // logged with a cause code, and reported back to the caller, instead
      // of swallowed silently (silent-failure-hunter finding 5): the UI must
      // not say "tokens removed" when this happened.
      revocationConfirmed = false;
      console.error(
        "[salesforce-client] disconnect: revoke request failed (network/timeout)",
        cause,
      );
    }
  }
  await deleteSalesforceConnection(customerRef);
  return { revocationConfirmed };
}
