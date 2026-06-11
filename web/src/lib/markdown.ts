// Shared markdown renderers. Lives in its own module (not lib/blog.ts) so
// client components can import it without pulling in node:fs from the blog
// loader. Anything LLM-returned that contains **bold**, lists, or [links]
// should be rendered through one of these instead of dropped into a <p>.
//
// All output is sanitized with DOMPurify before it reaches
// dangerouslySetInnerHTML. LLM output (and blog markdown) can carry raw
// HTML through `marked`, so without this a prompt-injected <script> or
// onerror attribute would execute in the customer's browser.
// isomorphic-dompurify works in both server components (Summary, blog)
// and client components (ChatPanel).

import { marked } from "marked";
import DOMPurify from "isomorphic-dompurify";

function sanitize(html: string): string {
  return DOMPurify.sanitize(html, {
    // Block-level markdown output: standard formatting tags only.
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["style", "form", "input", "button"],
    FORBID_ATTR: ["style"],
  });
}

/** Full block-level render. Wraps paragraphs in <p>, supports headings,
 *  lists, code blocks. Use with the `pk-prose` className on the wrapper.
 *  Output is sanitized; safe for dangerouslySetInnerHTML. */
export function renderMarkdown(md: string): string {
  return sanitize(marked.parse(md, { async: false }) as string);
}

/** Inline-only render. No <p> wrapper. Use inside chat bubbles, table
 *  cells, and other places where the surrounding layout already controls
 *  spacing. Supports **bold**, *italic*, `code`, and [links](url).
 *  Output is sanitized; safe for dangerouslySetInnerHTML. */
export function renderInlineMarkdown(md: string): string {
  return sanitize(marked.parseInline(md, { async: false }) as string);
}
