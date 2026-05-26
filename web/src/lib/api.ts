// Client for the Pricekeel FastAPI service. Server-side base URL (no secrets).
const API = process.env.PRICEKEEL_API ?? "http://localhost:8000";

export type Diagnostic = {
  overview: {
    booked_acv_won: number;
    price_realization_won: number;
    avg_discount_won: number;
    win_rate: number;
    won: number;
    lost: number;
    resolved_accounts: number;
  };
  leakage: {
    reference_threshold: number;
    excess_vs_reference_won: number;
    excess_pct_of_booked: number;
    off_policy_leakage_won: number;
    gross_discount_won: number;
  };
};

export async function getDemo(policy = 0.15): Promise<Diagnostic> {
  const res = await fetch(`${API}/demo?policy=${policy}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API responded ${res.status}`);
  return res.json();
}

export async function getSummary(
  policy = 0.15,
): Promise<{ enabled: boolean; summary: string | null }> {
  const res = await fetch(`${API}/summary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ policy }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API responded ${res.status}`);
  return res.json();
}
