import { customerRef, requireAccess } from "@/lib/gate";
import { describeSalesforceOpportunity } from "@/lib/salesforce-client";

export async function GET() {
  const denied = await requireAccess();
  if (denied) return denied;
  try {
    return Response.json({ fields: await describeSalesforceOpportunity(await customerRef()) });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "Could not read Salesforce metadata." },
      { status: 502 },
    );
  }
}
