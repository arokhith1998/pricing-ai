// Join class names, dropping falsy values. Not a Tailwind merger: primitives
// put their own classes first and the caller's className last, and the
// component-layer classes in globals.css lose to utilities by design.
export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}
