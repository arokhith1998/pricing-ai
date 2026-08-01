import { customerRef, requireAccess } from "@/lib/gate";
import { createSalesforceTask } from "@/lib/salesforce-client";
import {
  CRMUpstreamError,
  getSalesforceWorkflowLog,
  logSalesforceWorkflow,
  type SalesforceWorkflowInput,
} from "@/lib/salesforce-workspace";

export const maxDuration = 60;

const EVENTS = new Set<SalesforceWorkflowInput["event"]>([
  "flagged",
  "accepted",
  "override_requested",
  "approved",
  "rejected",
]);

export async function GET(req: Request) {
  const denied = await requireAccess();
  if (denied) return denied;
  const raw = Number(new URL(req.url).searchParams.get("limit") ?? 100);
  try {
    return Response.json(
      await getSalesforceWorkflowLog(
        await customerRef(),
        Number.isFinite(raw) ? raw : 100,
      ),
    );
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "Could not read workflow history." },
      { status: 502 },
    );
  }
}

export async function POST(req: Request) {
  const denied = await requireAccess();
  if (denied) return denied;
  let body: Partial<SalesforceWorkflowInput> & { writeback?: boolean };
  try {
    body = (await req.json()) as Partial<SalesforceWorkflowInput> & { writeback?: boolean };
  } catch {
    return Response.json({ error: "Expected a JSON workflow action." }, { status: 400 });
  }
  const event = body.event;
  const dealId = typeof body.deal_id === "string" ? body.deal_id.trim() : "";
  const actor = typeof body.actor === "string" ? body.actor.trim() : "";
  const justification =
    typeof body.justification === "string" ? body.justification.trim() : "";
  if (!event || !EVENTS.has(event) || !dealId || !actor) {
    return Response.json(
      { error: "A valid event, deal_id, and actor are required." },
      { status: 400 },
    );
  }
  if (event === "override_requested" && !justification) {
    return Response.json({ error: "Override justification is required." }, { status: 400 });
  }
  const requested = body.requested_discount_pct;
  if (
    requested !== undefined &&
    (typeof requested !== "number" || !Number.isFinite(requested) || requested < 0 || requested > 40)
  ) {
    return Response.json(
      { error: "requested_discount_pct must be between 0 and 40." },
      { status: 400 },
    );
  }
  const input: SalesforceWorkflowInput = {
    deal_id: dealId,
    event,
    actor: actor.slice(0, 200),
    justification: justification.slice(0, 2_000),
    requested_discount_pct: requested,
    outcome: body.outcome ?? "",
  };
  const customer = await customerRef();
  try {
    const result = await logSalesforceWorkflow(customer, input);
    const writeback = {
      requested: Boolean(body.writeback),
      success: false,
      task_id: "",
      error: "",
    };
    if (body.writeback) {
      try {
        const verdict = (result.verdict ?? {}) as Record<string, unknown>;
        const guidance = (result.guidance ?? {}) as Record<string, unknown>;
        const task = await createSalesforceTask(customer, {
          opportunityId: dealId,
          subject: `Pricekeel: ${event.replaceAll("_", " ")}`,
          description: [
            `Pricekeel event: ${event}`,
            `Actor: ${actor}`,
            `Account: ${String(guidance.account ?? "")}`,
            `Requested discount: ${Number(verdict.requested_pct ?? 0).toFixed(1)}%`,
            `Recommended discount: ${Number(verdict.recommended_pct ?? 0).toFixed(1)}%`,
            `Guardrail: ${Number(verdict.guardrail_pct ?? 0).toFixed(1)}%`,
            `Reference basis: ${String(verdict.reference_basis ?? "")}`,
            justification ? `Justification: ${justification}` : "",
            "Historical evidence is correlational; human approval remains authoritative.",
          ].filter(Boolean).join("\n"),
        });
        writeback.success = true;
        writeback.task_id = task.id;
      } catch {
        writeback.error = "Pricekeel logged the action, but Salesforce Task writeback failed.";
      }
    }
    return Response.json({ ...result, writeback });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "Could not log the workflow action." },
      { status: error instanceof CRMUpstreamError ? error.status : 502 },
    );
  }
}
