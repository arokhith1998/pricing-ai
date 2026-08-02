import "server-only";

import { fetchSalesforceCanonicalDeals } from "@/lib/salesforce-adapter";
import { markSalesforceSync, getSalesforceMapping } from "@/lib/salesforce-store";

const API = process.env.PRICEKEEL_API ?? "http://127.0.0.1:8000";
const API_TIMEOUT_MS = 55_000;

export class CRMUpstreamError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "CRMUpstreamError";
    this.status = status;
  }
}

async function crmFetch(
  path: string,
  customerRef: string,
  init: RequestInit = {},
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  try {
    return await fetch(`${API}${path}`, {
      ...init,
      headers: {
        "X-Pricekeel-Key": process.env.PRICEKEEL_API_KEY ?? "",
        "X-Pricekeel-Customer": customerRef,
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...(init.headers ?? {}),
      },
      cache: "no-store",
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }
}

async function upstreamJson(response: Response): Promise<Record<string, unknown>> {
  const body = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Pricing analysis failed.";
    const status = response.status >= 400 && response.status < 500
      && ![401, 403].includes(response.status)
      ? response.status
      : 502;
    throw new CRMUpstreamError(detail, status);
  }
  return body;
}

export async function loadSalesforceWorkspace(customerRef: string) {
  const config = await getSalesforceMapping(customerRef);
  const source = await fetchSalesforceCanonicalDeals(customerRef, config);
  const closed = source.records.filter((record) => record.outcome !== "open").length;
  const open = source.records.length - closed;
  let outcomesReconciled = 0;
  if (closed) {
    const reconciliation = await crmFetch("/crm/reconcile", customerRef, {
      method: "POST",
      body: JSON.stringify({
        outcomes: source.records
          .filter((record) => record.outcome !== "open")
          .map((record) => ({
            deal_id: record.opportunity_id,
            account: record.account_name,
            outcome: record.outcome,
          })),
      }),
    });
    const reconciled = await upstreamJson(reconciliation);
    outcomesReconciled = Number(reconciled.count ?? 0);
  }
  if (source.readiness.blockers.length) {
    await markSalesforceSync(customerRef, closed, open);
    return {
      mapping: config,
      source_readiness: source.readiness,
      analysis: null,
      guidance: [],
      engine_readiness: null,
      outcomes_reconciled: outcomesReconciled,
    };
  }
  const response = await crmFetch("/crm/analyze", customerRef, {
    method: "POST",
    body: JSON.stringify({
      records: source.records,
      policy_threshold_pct: config.policy_threshold_pct,
    }),
  });
  const result = await upstreamJson(response);
  await markSalesforceSync(customerRef, closed, open);
  return {
    mapping: config,
    source_readiness: source.readiness,
    analysis: result.analysis ?? null,
    guidance: result.guidance ?? [],
    engine_readiness: result.readiness ?? null,
    outcomes_reconciled: outcomesReconciled,
  };
}

export type SalesforceWorkflowInput = {
  deal_id: string;
  event: "flagged" | "accepted" | "override_requested" | "approved" | "rejected" | "outcome_recorded";
  actor: string;
  justification: string;
  requested_discount_pct?: number;
  outcome?: "closed_won" | "closed_lost" | "";
};

type CanonicalRecords = Awaited<
  ReturnType<typeof fetchSalesforceCanonicalDeals>
>["records"];

const DECIDES_OVERRIDE = new Set<SalesforceWorkflowInput["event"]>([
  "approved",
  "rejected",
]);

export async function logSalesforceWorkflow(
  customerRef: string,
  input: SalesforceWorkflowInput,
) {
  const config = await getSalesforceMapping(customerRef);
  // Approve and reject resolve terms Pricekeel already recorded, so they must
  // not depend on live evidence. Refetching here would block a pending
  // decision whenever the opportunity closed or the org fell below the
  // evidence floor, and would make approvals fail during a Salesforce outage.
  let records: CanonicalRecords = [];
  if (!DECIDES_OVERRIDE.has(input.event)) {
    const source = await fetchSalesforceCanonicalDeals(customerRef, config);
    if (source.readiness.blockers.length) {
      throw new Error(source.readiness.blockers.join(" "));
    }
    records = source.records;
  }
  const response = await crmFetch("/crm/workflow", customerRef, {
    method: "POST",
    body: JSON.stringify({
      ...input,
      records,
      policy_threshold_pct: config.policy_threshold_pct,
    }),
  });
  return upstreamJson(response);
}

export async function recordSalesforceWriteback(
  customerRef: string,
  input: {
    deal_id: string;
    actor: string;
    action_event: SalesforceWorkflowInput["event"];
    success: boolean;
    task_id?: string;
    error?: string;
  },
) {
  const response = await crmFetch("/crm/writeback", customerRef, {
    method: "POST",
    body: JSON.stringify(input),
  });
  return upstreamJson(response);
}

export async function getSalesforceWorkflowLog(
  customerRef: string,
  limit = 100,
) {
  const response = await crmFetch(
    `/crm/workflow?limit=${Math.min(Math.max(limit, 1), 200)}`,
    customerRef,
  );
  return upstreamJson(response);
}
