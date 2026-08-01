// Keep the central promise readable on the first paint. The earlier
// word-by-word blur made the most important sentence temporarily illegible and
// added client-side work to the LCP element.
const WORDS = ["Stop", "giving", "away", "price", "that", "wins", "you", "nothing."];

const H1_CLASS =
  "mx-auto max-w-3xl text-4xl font-extrabold leading-[1.08] tracking-tight text-fg sm:text-5xl";

const wordClass = (w: string) =>
  `mr-[0.25em] inline-block ${w === "nothing." ? "pk-headline-accent text-coral" : ""}`;

export default function HeroHeadline() {
  return (
    <h1 className={H1_CLASS}>
      {WORDS.map((w, i) => (
        <span key={i} className={wordClass(w)}>
          {w}
        </span>
      ))}
    </h1>
  );
}
