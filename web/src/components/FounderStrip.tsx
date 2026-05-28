"use client";

import Link from "next/link";

// Founder trust signal — short, plain, on-brand.
// TODO(adhithya): replace the placeholder bio + avatar URL below.
// - Avatar: drop a file into web/public/founder.jpg (a square, 400×400 is fine).
// - Bio: keep it to ONE LINE, "[role / prior credential], building Pricekeel."
// - LinkedIn URL: set NEXT_PUBLIC_FOUNDER_LINKEDIN in the env (optional).

const NAME = "Adhithya Bhaskar";
const BIO =
  "Founder, building Pricekeel. Background in pricing strategy and data; on a mission to make pricing decisions defensible.";
const LINKEDIN = process.env.NEXT_PUBLIC_FOUNDER_LINKEDIN;
const AVATAR = "/founder.jpg"; // drop file into web/public/

export default function FounderStrip() {
  return (
    <section className="rounded-2xl border border-mist bg-surface p-6">
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center sm:gap-6">
        <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-full border border-teal/40 bg-surface-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={AVATAR}
            alt={`${NAME}, founder`}
            className="h-full w-full object-cover"
            onError={(e) => {
              // Fall back to initials block if the image is not present yet.
              (e.currentTarget as HTMLImageElement).style.display = "none";
            }}
          />
          <span className="absolute inset-0 flex items-center justify-center text-xl font-semibold text-teal">
            {NAME.split(" ").map((n) => n[0]).join("")}
          </span>
        </div>
        <div className="text-center sm:text-left">
          <div className="text-xs font-semibold uppercase tracking-wider text-teal">
            Built by
          </div>
          <div className="mt-0.5 text-lg font-bold text-fg">{NAME}</div>
          <p className="mt-1 max-w-2xl text-sm text-muted">{BIO}</p>
          {LINKEDIN ? (
            <Link
              href={LINKEDIN}
              target="_blank"
              className="mt-2 inline-block text-xs font-medium text-teal hover:underline"
            >
              Connect on LinkedIn →
            </Link>
          ) : null}
        </div>
      </div>
    </section>
  );
}
