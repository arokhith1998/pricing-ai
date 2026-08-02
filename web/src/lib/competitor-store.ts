import "server-only";

import { randomUUID } from "node:crypto";
import { neon, type NeonQueryFunction } from "@neondatabase/serverless";

export type CompetitorClaim = {
  claim: string;
  confidence: "high" | "medium" | "low";
  evidence_excerpt: string;
};

export type CompetitorSource = {
  id: string;
  competitor_name: string;
  source_url: string;
  source_type: string;
  summary: string;
  claims: CompetitorClaim[];
  confidence: "high" | "medium" | "low";
  captured_at: string;
  last_verified_at: string;
};

let sqlClient: NeonQueryFunction<false, false> | null | undefined;
const memory = new Map<string, CompetitorSource[]>();

function db(): NeonQueryFunction<false, false> | null {
  if (sqlClient !== undefined) return sqlClient;
  const url = process.env.DATABASE_URL?.trim();
  sqlClient = url ? neon(url) : null;
  return sqlClient;
}

function iso(value: unknown): string {
  return value instanceof Date ? value.toISOString() : String(value ?? "");
}

function fromRow(row: Record<string, unknown>): CompetitorSource {
  return {
    id: String(row.id ?? ""),
    competitor_name: String(row.competitor_name ?? ""),
    source_url: String(row.source_url ?? ""),
    source_type: String(row.source_type ?? "other"),
    summary: String(row.summary ?? ""),
    claims: Array.isArray(row.claims) ? (row.claims as CompetitorClaim[]) : [],
    confidence: String(row.confidence ?? "medium") as CompetitorSource["confidence"],
    captured_at: iso(row.captured_at),
    last_verified_at: iso(row.last_verified_at),
  };
}

export async function listCompetitorSources(
  customerRef: string,
): Promise<CompetitorSource[]> {
  const sql = db();
  if (!sql) return [...(memory.get(customerRef) ?? [])];
  const rows = await sql`
    select id, competitor_name, source_url, source_type, summary, claims,
           confidence, captured_at, last_verified_at
    from competitor_context_sources
    where customer_ref = ${customerRef}
    order by last_verified_at desc
    limit 100
  `;
  return rows.map((row) => fromRow(row as Record<string, unknown>));
}

export async function saveCompetitorSource(
  customerRef: string,
  input: Omit<CompetitorSource, "id" | "captured_at" | "last_verified_at">,
): Promise<CompetitorSource> {
  const now = new Date().toISOString();
  const sql = db();
  if (!sql) {
    const rows = memory.get(customerRef) ?? [];
    const existing = rows.find((row) => row.source_url === input.source_url);
    const saved: CompetitorSource = {
      ...input,
      id: existing?.id ?? randomUUID(),
      captured_at: existing?.captured_at ?? now,
      last_verified_at: now,
    };
    memory.set(customerRef, [saved, ...rows.filter((row) => row.id !== saved.id)]);
    return saved;
  }
  const rows = await sql`
    insert into competitor_context_sources
      (customer_ref, competitor_name, source_url, source_type, summary, claims,
       confidence)
    values
      (${customerRef}, ${input.competitor_name}, ${input.source_url},
       ${input.source_type}, ${input.summary},
       ${JSON.stringify(input.claims)}::jsonb, ${input.confidence})
    on conflict (customer_ref, source_url) do update set
      competitor_name = excluded.competitor_name,
      source_type = excluded.source_type,
      summary = excluded.summary,
      claims = excluded.claims,
      confidence = excluded.confidence,
      last_verified_at = now()
    returning id, competitor_name, source_url, source_type, summary, claims,
              confidence, captured_at, last_verified_at
  `;
  return fromRow(rows[0] as Record<string, unknown>);
}

export async function deleteCompetitorSource(
  customerRef: string,
  id: string,
): Promise<boolean> {
  const sql = db();
  if (!sql) {
    const rows = memory.get(customerRef) ?? [];
    const kept = rows.filter((row) => row.id !== id);
    memory.set(customerRef, kept);
    return kept.length !== rows.length;
  }
  const rows = await sql`
    delete from competitor_context_sources
    where customer_ref = ${customerRef} and id = ${id}::uuid
    returning id
  `;
  return rows.length > 0;
}
