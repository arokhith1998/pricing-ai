import SalesforceWorkspace from "@/components/SalesforceWorkspace";

export const dynamic = "force-dynamic";

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
