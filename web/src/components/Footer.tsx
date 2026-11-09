import Link from "next/link";
import FooterDisclosure from "@/components/ui/FooterDisclosure";
import { FOOTER_COLUMNS } from "@/lib/site-nav";

export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="mt-16 border-t border-border">
      <div className="mx-auto max-w-page px-gutter py-10 sm:px-gutter-lg">
        <FooterDisclosure />
        <div className="mt-6 grid grid-cols-2 gap-x-6 gap-y-8 md:grid-cols-4">
          {FOOTER_COLUMNS.map((col) => (
            <nav key={col.title} aria-label={col.title}>
              <h2 className="pk-eyebrow text-muted">{col.title}</h2>
              <ul className="mt-2 flex flex-col">
                {col.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="pk-small inline-flex min-h-11 items-center text-muted hover:text-fg"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>
        <div className="pk-small mt-8 border-t border-border pt-6 text-muted">
          <span className="font-semibold text-fg">Price</span>
          <span className="font-semibold text-teal">keel</span>
          <span className="ml-2">© {year}</span>
        </div>
      </div>
    </footer>
  );
}
