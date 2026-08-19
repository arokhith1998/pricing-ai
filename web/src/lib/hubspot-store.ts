import "server-only";

// HubSpot-bound view of the shared CRM store (see crm-store.ts).

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
  type CrmMappingConfig,
} from "@/lib/crm-store";

const PROVIDER = "hubspot" as const;

export type HubspotConnection = CrmConnection;
export type HubspotMappingConfig = CrmMappingConfig;

export const DEFAULT_HUBSPOT_MAPPING: HubspotMappingConfig =
  defaultCrmMapping(PROVIDER);

export function saveHubspotConnection(
  input: Parameters<typeof saveCrmConnection>[1],
): Promise<void> {
  return saveCrmConnection(PROVIDER, input);
}

export function getHubspotConnection(
  customerRef: string,
): Promise<HubspotConnection | null> {
  return getCrmConnection(PROVIDER, customerRef);
}

export function updateHubspotTokens(
  customerRef: string,
  input: Parameters<typeof updateCrmTokens>[2],
): Promise<void> {
  return updateCrmTokens(PROVIDER, customerRef, input);
}

export function markHubspotConnection(
  customerRef: string,
  status: HubspotConnection["status"],
  error = "",
): Promise<void> {
  return markCrmConnection(PROVIDER, customerRef, status, error);
}

export function markHubspotSync(
  customerRef: string,
  closed: number,
  open: number,
): Promise<void> {
  return markCrmSync(PROVIDER, customerRef, closed, open);
}

export function deleteHubspotConnection(customerRef: string): Promise<void> {
  return deleteCrmConnection(PROVIDER, customerRef);
}

export function getHubspotMapping(
  customerRef: string,
): Promise<HubspotMappingConfig> {
  return getCrmMapping(PROVIDER, customerRef);
}

export function saveHubspotMapping(
  customerRef: string,
  config: HubspotMappingConfig,
): Promise<void> {
  return saveCrmMapping(PROVIDER, customerRef, config);
}

export function publicHubspotConnection(
  connection: HubspotConnection,
): Omit<HubspotConnection, "access_token" | "refresh_token"> {
  return publicCrmConnection(connection);
}
