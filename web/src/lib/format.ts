// Display formatters. Plain language, money first (design doc rule 4).

export const money = (x: number) => `$${Math.round(x).toLocaleString()}`;

/** Compact money for axis ticks and chips: $1.2M, $540K. */
export const moneyShort = (x: number) => {
  const a = Math.abs(x);
  if (a >= 1_000_000) return `$${(x / 1_000_000).toFixed(1)}M`;
  if (a >= 1_000) return `$${Math.round(x / 1_000)}K`;
  return `$${Math.round(x)}`;
};

export const pct = (x: number, digits = 1) => `${(x * 100).toFixed(digits)}%`;

export const pct0 = (x: number) => `${Math.round(x * 100)}%`;

/** "2026-05-27" -> "May 27, 2026" (UTC, locale-stable). */
export const fmtDate = (iso: string) =>
  new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
