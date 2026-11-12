import type { Metadata } from "next";
import SalesforceWorkspace from "@/components/SalesforceWorkspace";

export const dynamic = "force-dynamic";
// PK-116 (F17): reachable by direct URL only, behind the gate; never indexed.
export const metadata: Metadata = { title: "Customer workspace", robots: { index: false } };

export default async function CRMPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  return (
    <SalesforceWorkspace
      oauthConnected={params.connected === "1"}
      oauthError={typeof params.error === "string" ? params.error : ""}
    />
  );
}
