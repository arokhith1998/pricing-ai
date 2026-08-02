import { describe, expect, it } from "vitest";

import { validateSalesforceMapping } from "@/lib/salesforce-adapter";
import { DEFAULT_SALESFORCE_MAPPING } from "@/lib/salesforce-store";

describe("Salesforce field mapping", () => {
  it("rejects fields absent from the connected user's describe response", () => {
    const errors = validateSalesforceMapping(
      [{
        name: "Amount",
        label: "Amount",
        type: "currency",
        custom: false,
        nillable: true,
        calculated: false,
      }],
      {
        ...DEFAULT_SALESFORCE_MAPPING,
        mapping: {
          ...DEFAULT_SALESFORCE_MAPPING.mapping,
          list_value_field: "Secret_List_ACV__c",
        },
      },
    );

    expect(errors).toContain(
      "list_value_field references an unavailable Opportunity field.",
    );
  });
});
