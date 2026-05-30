import Link from "next/link";

export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="mt-16 border-t border-mist">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 py-8 text-sm text-muted sm:flex-row">
        <div>
          <span className="font-semibold text-fg">Price</span>
          <span className="font-semibold text-teal">keel</span>
          <span className="ml-2">© {year}</span>
        </div>
        <nav className="flex flex-wrap items-center justify-center gap-x-5 gap-y-1">
          <Link href="/sample" className="hover:text-fg">
            Sample
          </Link>
          <Link href="/pricing" className="hover:text-fg">
            Pricing
          </Link>
          <Link href="/blog" className="hover:text-fg">
            Blog
          </Link>
          <Link href="/brand" className="hover:text-fg">
            Brand
          </Link>
          <Link href="/trust" className="hover:text-fg">
            Trust
          </Link>
          <Link href="/privacy" className="hover:text-fg">
            Privacy
          </Link>
          <Link href="/terms" className="hover:text-fg">
            Terms
          </Link>
          <Link href="/subprocessors" className="hover:text-fg">
            Subprocessors
          </Link>
          <Link href="/licenses" className="hover:text-fg">
            Licenses
          </Link>
          <Link href="/upload" className="hover:text-fg">
            Your data
          </Link>
        </nav>
      </div>
    </footer>
  );
}
