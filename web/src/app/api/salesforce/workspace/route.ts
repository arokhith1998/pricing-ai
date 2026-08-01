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
    return Response.json(
      { error: error instanceof Error ? error.message : "Salesforce sync failed." },
      { status: 502 },
    );
  }
}
