import Link from "next/link";

// Bottom-of-page card that chains the funnel. The arrow nudges right on
// hover so the visitor feels invited forward.
export default function NextStep({
  href,
  eyebrow = "Next step",
  title,
  body,
}: {
  href: string;
  eyebrow?: string;
  title: string;
  body: string;
}) {
  return (
    <Link
      href={href}
      className="group block rounded-xl border border-teal/30 bg-surface p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-teal hover:shadow-md"
    >
      <div className="text-xs font-semibold uppercase tracking-wider text-teal">
        {eyebrow}
      </div>
      <div className="mt-1 flex items-center gap-2 text-lg font-semibold text-fg">
        {title}
        <span className="text-teal transition group-hover:translate-x-1">→</span>
      </div>
      <p className="mt-1 max-w-2xl text-sm text-muted">{body}</p>
    </Link>
  );
}
