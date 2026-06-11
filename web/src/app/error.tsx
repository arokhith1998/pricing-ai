"use client"; // Error boundaries must be Client Components

// Branded route-level error boundary. Note: Next.js 16 passes
// `unstable_retry` (re-fetch and re-render) alongside the legacy `reset`
// (re-render only); we prefer the former for transient server hiccups.

import { useEffect } from "react";
import Link from "next/link";

export default function Error({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  useEffect(() => {
    // Surface in the browser console; the digest matches server-side logs.
    console.error(error);
  }, [error]);

  return (
    <main className="mx-auto flex min-h-[60vh] max-w-3xl flex-col items-center justify-center px-6 py-24 text-center">
      <div className="text-xs font-semibold uppercase tracking-wider text-coral">
        Something went wrong
      </div>
      <h1 className="mt-3 text-3xl font-bold text-fg">
        That was not supposed to happen.
      </h1>
      <p className="mt-3 max-w-md text-muted">
        A temporary error interrupted this page. Trying again usually fixes
        it. If it keeps happening, tell us and we will look at the logs.
      </p>
      {error.digest ? (
        <p className="mt-2 text-xs text-muted">Error reference: {error.digest}</p>
      ) : null}
      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <button
          onClick={() => unstable_retry()}
          className="rounded-lg bg-teal px-5 py-2.5 text-sm font-semibold text-bg transition hover:scale-[1.02]"
        >
          Try again
        </button>
        <Link
          href="/"
          className="rounded-lg border border-mist bg-surface px-5 py-2.5 text-sm font-medium text-fg transition hover:border-teal"
        >
          Back to the homepage
        </Link>
      </div>
      <p className="mt-8 text-sm text-muted">
        Still stuck? Email{" "}
        <a
          href="mailto:adhithya@pricekeel.com"
          className="text-teal hover:underline"
        >
          adhithya@pricekeel.com
        </a>{" "}
        with the error reference above.
      </p>
    </main>
  );
}
