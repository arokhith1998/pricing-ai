"use client";

import { useEffect, useState } from "react";

// The hero proves the product is real with motion, not screenshots: a short,
// muted, looping screen recording of the diagnostic running on the sample data
// (upload, metrics animate, the leakage number lands).
//
// Until the MP4 is captured (see tools/capture-hero.md), the <video> shows its
// poster frame, a real screenshot of the diagnostic, so the hero is correct and
// shippable today. Drop hero-demo.mp4 into web/public/ and it goes live with no
// code change. Under prefers-reduced-motion we render the poster as a still.
export default function HeroDemo({
  poster = "/hero-poster.png",
  src = "/hero-demo.mp4",
  alt = "The Pricekeel diagnostic running on sample data: one CSV in, the leakage number out.",
}: {
  poster?: string;
  src?: string;
  alt?: string;
}) {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const m = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(m.matches);
    const on = (e: MediaQueryListEvent) => setReduced(e.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);

  const frame =
    "w-full rounded-2xl border border-border bg-surface shadow-2xl shadow-black/40";

  if (reduced) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={poster} alt={alt} className={frame} />;
  }

  return (
    <video
      className={frame}
      poster={poster}
      muted
      autoPlay
      loop
      playsInline
      preload="metadata"
      aria-label={alt}
    >
      <source src={src} type="video/mp4" />
    </video>
  );
}
