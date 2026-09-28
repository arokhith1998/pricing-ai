import { customerRef, requireAccess } from "@/lib/gate";
import { disconnectSalesforce } from "@/lib/salesforce-client";
import { SalesforceTokenDecryptionError } from "@/lib/salesforce-crypto";
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
  } catch (cause) {
    // A rotated SALESFORCE_TOKEN_ENCRYPTION_KEY makes crypto.subtle.decrypt
    // throw WebCrypto's own opaque DOMException text ("The operation failed
    // for an operation-specific reason"); answer with an actionable 4xx
    // instead of forwarding that as a 503 (silent-failure-hunter finding 5).
    if (cause instanceof SalesforceTokenDecryptionError) {
      return Response.json({ error: cause.message }, { status: 409 });
    }
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
    const { revocationConfirmed } = await disconnectSalesforce(await customerRef());
    // Local removal always happens (it is authoritative for Pricekeel), but
    // the refresh token can still be live at Salesforce if the revoke call
    // failed or was never confirmed: never let the UI say "tokens removed"
    // in that case (silent-failure-hunter finding 5).
    return Response.json({ disconnected: true, revocation_unconfirmed: !revocationConfirmed });
  } catch {
    return Response.json(
      { error: "Could not disconnect Salesforce." },
      { status: 502 },
    );
  }
}
