// Thin teal bar that tracks page scroll, for long-form routes only (blog posts,
// /methodology, /trust; see showsScrollProgress in lib/site-nav.ts). Pure CSS
// via animation-timeline: no JavaScript and no framer-motion, so the trust
// page stays free of motion libraries. Browsers without animation-timeline and
// prefers-reduced-motion visitors do not see it (rules in globals.css).
export default function ScrollProgress() {
  return <div aria-hidden className="pk-scroll-progress" />;
}
