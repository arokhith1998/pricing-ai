import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Page not found",
};

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-[60vh] max-w-3xl flex-col items-center justify-center px-6 py-24 text-center">
      <div className="text-xs font-semibold uppercase tracking-wider text-teal">
        404
      </div>
      <h1 className="mt-3 text-3xl font-bold text-fg">
        This page does not exist.
      </h1>
      <p className="mt-3 max-w-md text-muted">
        The link may be outdated, or the page may have moved. The diagnostic,
        the sample report, and the blog are all still where they should be.
      </p>
      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <Link
          href="/"
          className="rounded-lg bg-teal px-5 py-2.5 text-sm font-semibold text-bg transition hover:scale-[1.02]"
        >
          Back to the homepage
        </Link>
        <Link
          href="/sample"
          className="rounded-lg border border-mist bg-surface px-5 py-2.5 text-sm font-medium text-fg transition hover:border-teal"
        >
          See the sample report
        </Link>
      </div>
      <p className="mt-8 text-sm text-muted">
        Expected something here? Email{" "}
        <a
          href="mailto:adhithya@pricekeel.com"
          className="text-teal hover:underline"
        >
          adhithya@pricekeel.com
        </a>{" "}
        and it gets fixed.
      </p>
    </main>
  );
}
