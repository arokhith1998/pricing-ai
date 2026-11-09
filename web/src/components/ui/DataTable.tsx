import type { ReactNode } from "react";
import { cx } from "./cx";

// The wrapper's own fill is the scroll cover (last background layer in
// .pk-scroll-x), so set it to the surface the table sits on.
const COVER = {
  card: "[--pk-scroll-cover:var(--color-surface)]",
  inset: "[--pk-scroll-cover:var(--color-surface-2)]",
  canvas: "[--pk-scroll-cover:var(--color-bg)]",
} as const;

export type Column<Row> = {
  key: string;
  header: string;
  /** Right-aligned, tabular figures. */
  numeric?: boolean;
  /** Defaults to String(row[key]). */
  render?: (row: Row) => ReactNode;
};

// Server-rendered table for evidence and receipts. The caption is required: it
// names the scroll region for assistive tech. The first column is a sticky row
// header, numerics are right-aligned with tabular figures, and the wrapper
// scrolls horizontally with CSS edge fades on narrow screens. Cells are 14px.
export default function DataTable<Row extends Record<string, unknown>>({
  caption,
  columns,
  rows,
  surface = "card",
  className,
}: {
  caption: string;
  columns: ReadonlyArray<Column<Row>>;
  rows: ReadonlyArray<Row>;
  /** The surface the table sits on: sets the scroll-fade cover and the fill. */
  surface?: "card" | "inset" | "canvas";
  className?: string;
}) {
  return (
    <div
      role="region"
      aria-label={caption}
      tabIndex={0}
      className={cx("pk-scroll-x pk-surface-card", COVER[surface], className)}
    >
      <table className="w-full min-w-max border-collapse text-left text-small">
        <caption className="sr-only">{caption}</caption>
        <thead className="bg-surface-2">
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                className={cx(
                  "whitespace-nowrap border-b border-border px-4 py-3 font-semibold text-muted",
                  c.numeric && "text-right",
                )}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-border last:border-b-0 hover:bg-surface-2/60">
              {columns.map((c, ci) => {
                const content = c.render ? c.render(row) : String(row[c.key] ?? "");
                const base = "px-4 py-3 align-top";
                if (ci === 0) {
                  return (
                    <th
                      key={c.key}
                      scope="row"
                      className={cx(base, "sticky left-0 bg-[var(--pk-scroll-cover)] text-left font-medium text-fg")}
                    >
                      {content}
                    </th>
                  );
                }
                return (
                  <td
                    key={c.key}
                    className={cx(base, "text-muted", c.numeric && "text-right tabular-nums")}
                  >
                    {content}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
