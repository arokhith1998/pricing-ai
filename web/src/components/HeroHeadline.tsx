// The hero headline, plain server text at the Display size. It is the LCP
// element, so it carries no animation and no client work. Claim check: past
// the win point, deeper discount goes with a lower win rate in the synthetic
// book (the 25%+ band wins 42% against a 68% peak), so "has stopped winning
// deals" is supported where "wins you nothing" was not.
export const HERO_HEADLINE = "Stop giving away price that has stopped winning deals.";

export default function HeroHeadline() {
  return <h1 id="hero-h" className="pk-display m-0 max-w-[16ch] text-balance sm:max-w-[20ch]">{HERO_HEADLINE}</h1>;
}
