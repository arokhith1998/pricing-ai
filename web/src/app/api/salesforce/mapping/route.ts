import { customerRef, requireAccess } from "@/lib/gate";
import { describeSalesforceOpportunity } from "@/lib/salesforce-client";
import { validateSalesforceMapping } from "@/lib/salesforce-adapter";
import {
  DEFAULT_SALESFORCE_MAPPING,
  getSalesforceMapping,
  saveSalesforceMapping,
  type SalesforceMappingConfig,
} from "@/lib/salesforce-store";

export async function GET() {
  const denied = await requireAccess();
  if (denied) return denied;
  try {
    return Response.json({ mapping: await getSalesforceMapping(await customerRef()) });
  } catch {
    return Response.json({ error: "Could not read the field mapping." }, { status: 503 });
  }
}
export async function PUT(req: Request) {
  const denied = await requireAccess();
  if (denied) return denied;
  let input: Partial<SalesforceMappingConfig>;
  try {
    input = (await req.json()) as Partial<SalesforceMappingConfig>;
  } catch {
    return Response.json({ error: "Expected a JSON mapping." }, { status: 400 });
  }
  const config: SalesforceMappingConfig = {
    mapping: {
      ...DEFAULT_SALESFORCE_MAPPING.mapping,
      ...(input.mapping ?? {}),
    },
    policy_threshold_pct: Number(input.policy_threshold_pct),
    default_value_metric:
      input.default_value_metric ?? DEFAULT_SALESFORCE_MAPPING.default_value_metric,
  };
  try {
    const customer = await customerRef();
    const fields = await describeSalesforceOpportunity(customer);
    const errors = validateSalesforceMapping(fields, config);
    if (errors.length) return Response.json({ error: errors.join(" ") }, { status: 400 });
    await saveSalesforceMapping(customer, config);
    return Response.json({ mapping: config });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "Could not save the field mapping." },
      { status: 502 },
    );
  }
}
