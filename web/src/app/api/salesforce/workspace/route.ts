import { customerRef, requireAccess } from "@/lib/gate";
import { getSalesforceConnection, publicSalesforceConnection } from "@/lib/salesforce-store";
import { loadSalesforceWorkspace } from "@/lib/salesforce-workspace";

export const maxDuration = 60;

export async function GET() {
  const denied = await requireAccess();
  if (denied) return denied;
  const customer = await customerRef();
  try {
    const connection = await getSalesforceConnection(customer);
    if (!connection) {
      return Response.json({ error: "Connect Salesforce before syncing." }, { status: 409 });
    }
    const workspace = await loadSalesforceWorkspace(customer);
    return Response.json({
      ...workspace,
      connection: publicSalesforceConnection(connection),
      synced_at: new Date().toISOString(),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Salesforce sync failed.";
    // A sync failure is usually an expired or revoked token: the client has
    // already flipped the stored status to reauth_required. Return the current
    // connection (with that status) as a degraded 200 so the workspace can show
    // a Reconnect prompt instead of a bare error over a stale "Connected"
    // banner. Only a genuinely missing connection stays a hard 502.
    let current = null;
    try {
      current = await getSalesforceConnection(customer);
    } catch {
      current = null;
    }
    if (current) {
      return Response.json(
        { connection: publicSalesforceConnection(current), degraded: true, error: message },
        { status: 200 },
      );
    }
    return Response.json({ error: message }, { status: 502 });
  }
}
