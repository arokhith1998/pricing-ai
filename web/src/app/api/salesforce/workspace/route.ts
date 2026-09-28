import { customerRef, requireAccess } from "@/lib/gate";
import { SalesforceTokenDecryptionError } from "@/lib/salesforce-crypto";
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
    // A rotated SALESFORCE_TOKEN_ENCRYPTION_KEY makes crypto.subtle.decrypt
    // throw WebCrypto's own opaque DOMException text; answer with a clear,
    // actionable 4xx instead of a degraded/502 wrapping that text
    // (silent-failure-hunter finding 5). This is a decryption problem, not a
    // Salesforce session problem, so it must not read as "needs
    // reauthorization" either: reconnecting cannot fix it (the stored row
    // itself needs to be replaced), so it takes its own status ahead of the
    // degraded/502 classification below.
    if (error instanceof SalesforceTokenDecryptionError) {
      return Response.json({ error: error.message }, { status: 409 });
    }
    const message = error instanceof Error ? error.message : "Salesforce sync failed.";
    // A sync failure is usually an expired or revoked token: the client has
    // already flipped the stored status to reauth_required. Return the current
    // connection (with that status) as a degraded 200 so the workspace can show
    // a Reconnect prompt instead of a bare error over a stale "Connected"
    // banner.
    //
    // `degraded` is reserved for that case (silent-failure-hunter finding 3):
    // loadSalesforceWorkspace() already catches a data-readiness refusal from
    // the pricing engine (insufficient closed-deal bands, multiple
    // currencies, a degenerate list mapping, ...) and turns it into a
    // readiness blocker on a normal 200, so an error still reaching here is
    // either a genuine connection problem or an unrelated outage. Check the
    // CURRENT status, not merely that a connection row still exists: a
    // connection that is still "connected" but hit some other failure (e.g.
    // FastAPI itself unreachable) must not flip the UI to "Reconnect
    // Salesforce" for a problem reconnecting cannot fix.
    let current = null;
    try {
      current = await getSalesforceConnection(customer);
    } catch {
      current = null;
    }
    if (current && current.status !== "connected") {
      return Response.json(
        { connection: publicSalesforceConnection(current), degraded: true, error: message },
        { status: 200 },
      );
    }
    return Response.json({ error: message }, { status: 502 });
  }
}
