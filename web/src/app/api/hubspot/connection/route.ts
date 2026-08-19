import { customerRef, requireAccess } from "@/lib/gate";
import { disconnectHubspot } from "@/lib/hubspot-client";
import { hubspotOAuthConfigured } from "@/lib/hubspot-oauth";
import {
  getHubspotConnection,
  publicHubspotConnection,
} from "@/lib/hubspot-store";

export async function GET() {
  const denied = await requireAccess();
  if (denied) return denied;
  const customer = await customerRef();
  try {
    const connection = await getHubspotConnection(customer);
    return Response.json({
      configured: hubspotOAuthConfigured(),
      connected: Boolean(connection),
      connection: connection ? publicHubspotConnection(connection) : null,
    });
  } catch {
    return Response.json(
      { error: "Could not read the HubSpot connection." },
      { status: 503 },
    );
  }
}

export async function DELETE() {
  const denied = await requireAccess();
  if (denied) return denied;
  try {
    await disconnectHubspot(await customerRef());
    return Response.json({ disconnected: true });
  } catch {
    return Response.json(
      { error: "Could not disconnect HubSpot." },
      { status: 502 },
    );
  }
}
