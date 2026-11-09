import type { ReactNode } from "react";
import { cx } from "./cx";

export type SectionBand = "canvas" | "band" | "spotlight";
export type SectionWidth = "page" | "prose" | "app";

const BANDS: Record<SectionBand, string> = {
  canvas: "",
  band: "pk-band",
  spotlight: "pk-band-spotlight",
};

const WIDTHS: Record<SectionWidth, string> = {
  page: "max-w-page",
  prose: "max-w-prose-page",
  app: "max-w-app",
};

// A page section: vertical rhythm 48/64/96px, a width container with 16/24px
// gutters, and one of three bands. Adjacent sections must not share a band.
// A section with a heading should pass `labelledBy` (the heading's id).
export default function Section({
  band = "canvas",
  width = "page",
  id,
  labelledBy,
  className,
  children,
}: {
  band?: SectionBand;
  width?: SectionWidth;
  id?: string;
  labelledBy?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section
      id={id}
      aria-labelledby={labelledBy}
      data-band={band}
      className={cx("scroll-mt-24", BANDS[band])}
    >
      <div
        className={cx(
          "mx-auto px-gutter py-section-sm sm:px-gutter-lg md:py-section-md lg:py-section-lg",
          WIDTHS[width],
          className,
        )}
      >
        {children}
      </div>
    </section>
  );
}
