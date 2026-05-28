// Small intro panel at the top of each main page. Tells a new user what
// they are looking at and what to look at first.
export default function PageGuide({
  eyebrow = "Reading this page",
  title,
  body,
  bullets,
}: {
  eyebrow?: string;
  title: string;
  body: string;
  bullets?: string[];
}) {
  return (
    <section className="rounded-xl border border-teal/25 bg-surface/60 p-5 backdrop-blur-sm">
      <div className="text-xs font-semibold uppercase tracking-wider text-teal">
        {eyebrow}
      </div>
      <h2 className="mt-1 text-lg font-semibold text-fg">{title}</h2>
      <p className="mt-1 max-w-2xl text-sm text-muted">{body}</p>
      {bullets?.length ? (
        <ul className="mt-3 space-y-1.5 text-sm text-ink">
          {bullets.map((b, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-teal">•</span>
              <span>{b}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
