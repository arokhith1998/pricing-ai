import { customerRef, requireAccess } from "@/lib/gate";
import { disconnectSalesforce } from "@/lib/salesforce-client";
import { salesforceOAuthConfigured } from "@/lib/salesforce-oauth";
import {
  getSalesforceConnection,
  publicSalesforceConnection,
} from "@/lib/salesforce-store";

export async function GET() {
  const denied = await requireAccess();
  if (denied) return denied;
  const customer = await customerRef();
  try {
    const connection = await getSalesforceConnection(customer);
    return Response.json({
      configured: salesforceOAuthConfigured(),
      connected: Boolean(connection),
      connection: connection ? publicSalesforceConnection(connection) : null,
    });
  } catch {
    return Response.json(
      { error: "Could not read the Salesforce connection." },
      { status: 503 },
    );
  }
}
export async function DELETE() {
  const denied = await requireAccess();
  if (denied) return denied;
  try {
    await disconnectSalesforce(await customerRef());
    return Response.json({ disconnected: true });
  } catch {
    return Response.json(
      { error: "Could not disconnect Salesforce." },
      { status: 502 },
    );
  }
}
