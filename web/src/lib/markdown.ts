// Shared markdown renderers. Lives in its own module (not lib/blog.ts) so
// client components can import it without pulling in node:fs from the blog
// loader. Anything LLM-returned that contains **bold**, lists, or [links]
// should be rendered through one of these instead of dropped into a <p>.

import { marked } from "marked";

/** Full block-level render. Wraps paragraphs in <p>, supports headings,
 *  lists, code blocks. Use with the `pk-prose` className on the wrapper. */
export function renderMarkdown(md: string): string {
  return marked.parse(md, { async: false }) as string;
}

/** Inline-only render. No <p> wrapper. Use inside chat bubbles, table
 *  cells, and other places where the surrounding layout already controls
 *  spacing. Supports **bold**, *italic*, `code`, and [links](url). */
export function renderInlineMarkdown(md: string): string {
  return marked.parseInline(md, { async: false }) as string;
}
