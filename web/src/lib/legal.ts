// Single source of truth for the legal-entity fill-ins that recur across
// /terms, /privacy, and any future legal page.
//
// WHY THIS EXISTS: before incorporation these were hardcoded "[legal entity]"
// strings scattered across pages. The 2026-05-30 legal audit calls for the
// entity name to be one variable to fill in once the Delaware C-Corp is formed.
//
// AFTER INCORPORATION: set these in the Vercel project env and redeploy. No
// code change, no bracket-hunting:
//   NEXT_PUBLIC_LEGAL_ENTITY="Pricekeel, Inc."
//   NEXT_PUBLIC_LEGAL_JURISDICTION="Delaware, USA"
//   NEXT_PUBLIC_GOVERNING_LAW="Delaware, USA"          (optional; defaults below)
//   NEXT_PUBLIC_LEGAL_VENUE="New Castle County, Delaware"  (optional)
//
// The bracketed fallbacks render visibly as placeholders so an unfilled value
// is obvious on the live page rather than silently wrong.

export const LEGAL_ENTITY = process.env.NEXT_PUBLIC_LEGAL_ENTITY ?? "[legal entity]";
export const LEGAL_JURISDICTION =
  process.env.NEXT_PUBLIC_LEGAL_JURISDICTION ?? "[jurisdiction]";
export const GOVERNING_LAW =
  process.env.NEXT_PUBLIC_GOVERNING_LAW ?? "[Delaware, USA]";
export const LEGAL_VENUE =
  process.env.NEXT_PUBLIC_LEGAL_VENUE ?? "[New Castle County, Delaware]";

// True once the entity name has actually been filled in (i.e. the env var is
// set to something other than the bracketed placeholder). Useful if a page
// wants to drop a "pending incorporation" note once the entity is real.
export const ENTITY_FILLED = !LEGAL_ENTITY.startsWith("[");
