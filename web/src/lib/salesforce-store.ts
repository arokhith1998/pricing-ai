import "server-only";

import { neon, type NeonQueryFunction } from "@neondatabase/serverless";
import {
  decryptSalesforceSecret,
  encryptSalesforceSecret,
} from "@/lib/salesforce-crypto";

export type SalesforceConnection = {
  customer_ref: string;
  org_id: string;
  user_id: string;
  instance_url: string;
  access_token: string;
  refresh_token: string;
  token_type: string;
  scope: string;
  issued_at: string;
  status: "connected" | "reauth_required" | "error";
  last_error: string;
  last_sync_at: string | null;
  last_sync_closed: number;
  last_sync_open: number;
  connected_at: string;
  updated_at: string;
};

export type SalesforceFieldMapping = {
  list_value_field: string;
  booked_value_field: string;
  segment_field: string;
  product_field: string;
  value_metric_field: string;
  competitor_field: string;
  approved_by_field: string;
  term_months_field: string;
};

export type SalesforceMappingConfig = {
  mapping: SalesforceFieldMapping;
  policy_threshold_pct: number;
  default_value_metric: "seats" | "consumption" | "hybrid";
};

export const DEFAULT_SALESFORCE_MAPPING: SalesforceMappingConfig = {
  mapping: {
    list_value_field: "",
    booked_value_field: "Amount",
    segment_field: "",
    product_field: "",
    value_metric_field: "",
    competitor_field: "",
    approved_by_field: "",
    term_months_field: "",
  },
  policy_threshold_pct: 15,
  default_value_metric: "hybrid",
};

type StoredConnection = Omit<
  SalesforceConnection,
  "access_token" | "refresh_token"
> & {
  access_token_encrypted: string;
  refresh_token_encrypted: string;
};

let sqlClient: NeonQueryFunction<false, false> | null | undefined;

function db(): NeonQueryFunction<false, false> | null {
  if (sqlClient !== undefined) return sqlClient;
  const url = process.env.DATABASE_URL?.trim();
  if (!url && process.env.VERCEL_ENV === "production") {
    throw new Error("DATABASE_URL is required for durable Salesforce connections.");
  }
  sqlClient = url ? neon(url) : null;
  return sqlClient;
}

const memoryConnections = new Map<string, StoredConnection>();
const memoryMappings = new Map<string, SalesforceMappingConfig>();

function iso(value: unknown): string | null {
  if (!value) return null;
  if (value instanceof Date) return value.toISOString();
  return String(value);
}

function storedFromRow(row: Record<string, unknown>): StoredConnection {
  return {
    customer_ref: String(row.customer_ref ?? ""),
    org_id: String(row.org_id ?? ""),
    user_id: String(row.user_id ?? ""),
    instance_url: String(row.instance_url ?? ""),
    access_token_encrypted: String(row.access_token_encrypted ?? ""),
    refresh_token_encrypted: String(row.refresh_token_encrypted ?? ""),
    token_type: String(row.token_type ?? "Bearer"),
    scope: String(row.scope ?? ""),
    issued_at: String(row.issued_at ?? ""),
    status: (row.status ?? "connected") as StoredConnection["status"],
    last_error: String(row.last_error ?? ""),
    last_sync_at: iso(row.last_sync_at),
    last_sync_closed: Number(row.last_sync_closed ?? 0),
    last_sync_open: Number(row.last_sync_open ?? 0),
    connected_at: iso(row.connected_at) ?? new Date().toISOString(),
    updated_at: iso(row.updated_at) ?? new Date().toISOString(),
  };
}

async function decryptConnection(
  row: StoredConnection,
): Promise<SalesforceConnection> {
  const { access_token_encrypted, refresh_token_encrypted, ...safe } = row;
  return {
    ...safe,
    access_token: await decryptSalesforceSecret(access_token_encrypted),
    refresh_token: await decryptSalesforceSecret(refresh_token_encrypted),
  };
}

export async function saveSalesforceConnection(input: {
  customer_ref: string;
  org_id: string;
  user_id: string;
  instance_url: string;
  access_token: string;
  refresh_token: string;
  token_type?: string;
  scope?: string;
  issued_at?: string;
}): Promise<void> {
  const access = await encryptSalesforceSecret(input.access_token);
  const refresh = await encryptSalesforceSecret(input.refresh_token);
  const now = new Date().toISOString();
  const row: StoredConnection = {
    customer_ref: input.customer_ref,
    org_id: input.org_id,
    user_id: input.user_id,
    instance_url: input.instance_url,
    access_token_encrypted: access,
    refresh_token_encrypted: refresh,
    token_type: input.token_type ?? "Bearer",
    scope: input.scope ?? "",
    issued_at: input.issued_at ?? "",
    status: "connected",
    last_error: "",
    last_sync_at: null,
    last_sync_closed: 0,
    last_sync_open: 0,
    connected_at: now,
    updated_at: now,
  };
  const sql = db();
  if (!sql) {
    memoryConnections.set(input.customer_ref, row);
    if (!memoryMappings.has(input.customer_ref)) {
      memoryMappings.set(input.customer_ref, structuredClone(DEFAULT_SALESFORCE_MAPPING));
    }
    return;
  }
  await sql`
    insert into salesforce_connections
      (customer_ref, org_id, user_id, instance_url, access_token_encrypted,
       refresh_token_encrypted, token_type, scope, issued_at, status,
       last_error, updated_at)
    values
      (${input.customer_ref}, ${input.org_id}, ${input.user_id},
       ${input.instance_url}, ${access}, ${refresh}, ${row.token_type},
       ${row.scope}, ${row.issued_at}, 'connected', '', now())
    on conflict (customer_ref) do update set
      org_id = excluded.org_id,
      user_id = excluded.user_id,
      instance_url = excluded.instance_url,
      access_token_encrypted = excluded.access_token_encrypted,
      refresh_token_encrypted = excluded.refresh_token_encrypted,
      token_type = excluded.token_type,
      scope = excluded.scope,
      issued_at = excluded.issued_at,
      status = 'connected',
      last_error = '',
      updated_at = now()
  `;
  await sql`
    insert into salesforce_mappings (customer_ref)
    values (${input.customer_ref})
    on conflict (customer_ref) do nothing
  `;
}

export async function getSalesforceConnection(
  customerRef: string,
): Promise<SalesforceConnection | null> {
  const sql = db();
  let stored: StoredConnection | undefined;
  if (!sql) {
    stored = memoryConnections.get(customerRef);
  } else {
    const rows = await sql`
      select * from salesforce_connections
      where customer_ref = ${customerRef}
      limit 1
    `;
    if (rows[0]) stored = storedFromRow(rows[0] as Record<string, unknown>);
  }
  return stored ? decryptConnection(stored) : null;
}

export async function updateSalesforceTokens(
  customerRef: string,
  input: {
    access_token: string;
    refresh_token?: string;
    instance_url?: string;
    token_type?: string;
    scope?: string;
    issued_at?: string;
  },
): Promise<void> {
  const current = await getSalesforceConnection(customerRef);
  if (!current) throw new Error("Salesforce connection not found.");
  const access = await encryptSalesforceSecret(input.access_token);
  const refresh = await encryptSalesforceSecret(
    input.refresh_token || current.refresh_token,
  );
  const instanceUrl = input.instance_url || current.instance_url;
  const tokenType = input.token_type || current.token_type;
  const scope = input.scope || current.scope;
  const issuedAt = input.issued_at || current.issued_at;
  const sql = db();
  if (!sql) {
    const row = memoryConnections.get(customerRef);
    if (!row) throw new Error("Salesforce connection not found.");
    row.access_token_encrypted = access;
    row.refresh_token_encrypted = refresh;
    row.instance_url = instanceUrl;
    row.token_type = tokenType;
    row.scope = scope;
    row.issued_at = issuedAt;
    row.status = "connected";
    row.last_error = "";
    row.updated_at = new Date().toISOString();
    return;
  }
  await sql`
    update salesforce_connections
    set access_token_encrypted = ${access},
        refresh_token_encrypted = ${refresh},
        instance_url = ${instanceUrl}, token_type = ${tokenType},
        scope = ${scope}, issued_at = ${issuedAt}, status = 'connected',
        last_error = '', updated_at = now()
    where customer_ref = ${customerRef}
  `;
}

export async function markSalesforceConnection(
  customerRef: string,
  status: SalesforceConnection["status"],
  error = "",
): Promise<void> {
  const sql = db();
  if (!sql) {
    const row = memoryConnections.get(customerRef);
    if (row) {
      row.status = status;
      row.last_error = error.slice(0, 500);
      row.updated_at = new Date().toISOString();
    }
    return;
  }
  await sql`
    update salesforce_connections
    set status = ${status}, last_error = ${error.slice(0, 500)}, updated_at = now()
    where customer_ref = ${customerRef}
  `;
}

export async function markSalesforceSync(
  customerRef: string,
  closed: number,
  open: number,
): Promise<void> {
  const sql = db();
  if (!sql) {
    const row = memoryConnections.get(customerRef);
    if (row) {
      row.last_sync_at = new Date().toISOString();
      row.last_sync_closed = closed;
      row.last_sync_open = open;
      row.status = "connected";
      row.last_error = "";
      row.updated_at = row.last_sync_at;
    }
    return;
  }
  await sql`
    update salesforce_connections
    set last_sync_at = now(), last_sync_closed = ${closed},
        last_sync_open = ${open}, status = 'connected', last_error = '',
        updated_at = now()
    where customer_ref = ${customerRef}
  `;
}

export async function deleteSalesforceConnection(customerRef: string): Promise<void> {
  const sql = db();
  if (!sql) {
    memoryConnections.delete(customerRef);
    memoryMappings.delete(customerRef);
    return;
  }
  await sql`
    delete from salesforce_connections where customer_ref = ${customerRef}
  `;
}

export async function getSalesforceMapping(
  customerRef: string,
): Promise<SalesforceMappingConfig> {
  const sql = db();
  if (!sql) {
    return (
      memoryMappings.get(customerRef) ??
      structuredClone(DEFAULT_SALESFORCE_MAPPING)
    );
  }
  const rows = await sql`
    select mapping, policy_threshold_pct, default_value_metric
    from salesforce_mappings
    where customer_ref = ${customerRef}
    limit 1
  `;
  if (!rows[0]) return structuredClone(DEFAULT_SALESFORCE_MAPPING);
  const row = rows[0] as Record<string, unknown>;
  return {
    mapping: {
      ...DEFAULT_SALESFORCE_MAPPING.mapping,
      ...((row.mapping as Partial<SalesforceFieldMapping> | null) ?? {}),
    },
    policy_threshold_pct: Number(row.policy_threshold_pct ?? 15),
    default_value_metric: String(
      row.default_value_metric ?? "hybrid",
    ) as SalesforceMappingConfig["default_value_metric"],
  };
}

export async function saveSalesforceMapping(
  customerRef: string,
  config: SalesforceMappingConfig,
): Promise<void> {
  const normalized: SalesforceMappingConfig = {
    mapping: { ...DEFAULT_SALESFORCE_MAPPING.mapping, ...config.mapping },
    policy_threshold_pct: config.policy_threshold_pct,
    default_value_metric: config.default_value_metric,
  };
  const sql = db();
  if (!sql) {
    memoryMappings.set(customerRef, normalized);
    return;
  }
  await sql`
    insert into salesforce_mappings
      (customer_ref, mapping, policy_threshold_pct, default_value_metric)
    values
      (${customerRef}, ${JSON.stringify(normalized.mapping)}::jsonb,
       ${normalized.policy_threshold_pct}, ${normalized.default_value_metric})
    on conflict (customer_ref) do update set
      mapping = excluded.mapping,
      policy_threshold_pct = excluded.policy_threshold_pct,
      default_value_metric = excluded.default_value_metric,
      updated_at = now()
  `;
}

export function publicSalesforceConnection(
  connection: SalesforceConnection,
): Omit<SalesforceConnection, "access_token" | "refresh_token"> {
  return {
    customer_ref: connection.customer_ref,
    org_id: connection.org_id,
    user_id: connection.user_id,
    instance_url: connection.instance_url,
    token_type: connection.token_type,
    scope: connection.scope,
    issued_at: connection.issued_at,
    status: connection.status,
    last_error: connection.last_error,
    last_sync_at: connection.last_sync_at,
    last_sync_closed: connection.last_sync_closed,
    last_sync_open: connection.last_sync_open,
    connected_at: connection.connected_at,
    updated_at: connection.updated_at,
  };
}
