import "server-only";

// Salesforce-bound view of the shared CRM store. The implementation lives in
// crm-store.ts; this module fixes the provider so call sites read as Salesforce
// code and can never accidentally address a HubSpot row.

import {
  defaultCrmMapping,
  deleteCrmConnection,
  getCrmConnection,
  getCrmMapping,
  markCrmConnection,
  markCrmSync,
  publicCrmConnection,
  saveCrmConnection,
  saveCrmMapping,
  updateCrmTokens,
  type CrmConnection,
  type CrmFieldMapping,
  type CrmMappingConfig,
} from "@/lib/crm-store";

const PROVIDER = "salesforce" as const;

export type SalesforceConnection = CrmConnection;
export type SalesforceFieldMapping = CrmFieldMapping;
export type SalesforceMappingConfig = CrmMappingConfig;

export const DEFAULT_SALESFORCE_MAPPING: SalesforceMappingConfig =
  defaultCrmMapping(PROVIDER);

export function saveSalesforceConnection(
  input: Parameters<typeof saveCrmConnection>[1],
): Promise<void> {
  return saveCrmConnection(PROVIDER, input);
}

export function getSalesforceConnection(
  customerRef: string,
): Promise<SalesforceConnection | null> {
  return getCrmConnection(PROVIDER, customerRef);
}

export function updateSalesforceTokens(
  customerRef: string,
  input: Parameters<typeof updateCrmTokens>[2],
): Promise<void> {
  return updateCrmTokens(PROVIDER, customerRef, input);
}

export function markSalesforceConnection(
  customerRef: string,
  status: SalesforceConnection["status"],
  error = "",
): Promise<void> {
  return markCrmConnection(PROVIDER, customerRef, status, error);
}

export function markSalesforceSync(
  customerRef: string,
  closed: number,
  open: number,
): Promise<void> {
  return markCrmSync(PROVIDER, customerRef, closed, open);
}

export function deleteSalesforceConnection(customerRef: string): Promise<void> {
  return deleteCrmConnection(PROVIDER, customerRef);
}

export function getSalesforceMapping(
  customerRef: string,
): Promise<SalesforceMappingConfig> {
  return getCrmMapping(PROVIDER, customerRef);
}

export function saveSalesforceMapping(
  customerRef: string,
  config: SalesforceMappingConfig,
): Promise<void> {
  return saveCrmMapping(PROVIDER, customerRef, config);
}

export function publicSalesforceConnection(
  connection: SalesforceConnection,
): Omit<SalesforceConnection, "access_token" | "refresh_token"> {
  return publicCrmConnection(connection);
}
