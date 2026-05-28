// A slow, GPU-cheap aurora behind every page. CSS-only animation; respects
// prefers-reduced-motion via the override in globals.css.
export default function AuroraBackground() {
  return <div className="pk-aurora" aria-hidden />;
}
