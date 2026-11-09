// One static spotlight behind the top of the page. No scroll listener, no
// parallax, no animation, no JavaScript, no framer-motion. Geometry and color
// live in the .pk-spotlight class in globals.css.
export default function AuroraBackground() {
  return <div aria-hidden className="pk-spotlight" />;
}
