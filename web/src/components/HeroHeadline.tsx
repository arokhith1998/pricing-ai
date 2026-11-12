// The hero headline, plain server text at the Display size. It is the LCP
// element, so it carries no animation and no client work. The sentence is the
// founder's positioning line from the research sheet (Opportunity tab, the
// 10-word clarity test). It states what Pricekeel exists to do. It is
// positioning, not a result: no customer, figure or outcome is claimed.
export const HERO_HEADLINE = "See which customers cost more to serve than they pay.";

export default function HeroHeadline() {
  return <h1 id="hero-h" className="pk-display m-0 max-w-[16ch] text-balance sm:max-w-[20ch]">{HERO_HEADLINE}</h1>;
}
