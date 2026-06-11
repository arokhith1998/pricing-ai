// Shared markdown renderers. Lives in its own module (not lib/blog.ts) so
// client components can import it without pulling in node:fs from the blog
// loader. Anything LLM-returned that contains **bold**, lists, or [links]
// should be rendered through one of these instead of dropped into a <p>.
//
// All output is sanitized before it reaches dangerouslySetInnerHTML. LLM
// output (and blog markdown) can carry raw HTML through `marked`, so without
// this a prompt-injected <script> or onerror attribute would execute in the
// customer's browser.
//
// sanitize-html (htmlparser2-based, no DOM emulation) is used instead of
// isomorphic-dompurify: DOMPurify's server path requires jsdom, which fails
// at module evaluation in the Vercel serverless runtime and 500'd every page
// importing this module (found live 2026-06-11).

import { marked } from "marked";
import sanitizeHtml from "sanitize-html";

const SANITIZE_OPTIONS: sanitizeHtml.IOptions = {
  // Standard block + inline formatting tags marked can emit. No style/form
  // controls, no iframes, no SVG/MathML.
  allowedTags: [
    "a", "p", "br", "hr", "blockquote",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "strong", "em", "b", "i", "s", "del", "sup", "sub",
    "code", "pre",
    "table", "thead", "tbody", "tr", "th", "td",
    "img",
  ],
  allowedAttributes: {
    a: ["href", "title", "target", "rel"],
    img: ["src", "alt", "title"],
    th: ["align"],
    td: ["align"],
    code: ["class"], // language-* classes from fenced blocks
  },
  allowedSchemes: ["http", "https", "mailto"],
  // Drop disallowed tags entirely (default keeps their text content, which
  // is what we want for e.g. a stray <script>alert(1)</script>: text stays,
  // tag goes).
  disallowedTagsMode: "discard",
};

function sanitize(html: string): string {
  return sanitizeHtml(html, SANITIZE_OPTIONS);
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
