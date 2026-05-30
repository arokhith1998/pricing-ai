// /brand — public brand kit. Listed so a journalist, partner, or
// internal teammate can grab the right asset at the right size without
// asking. Linked from the footer.

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Brand kit · Pricekeel",
  description:
    "Pricekeel logo, mark, wordmark, and social cover assets for press, partners, and decks.",
};

type Asset = {
  label: string;
  filename: string;
  size: string;
  format: string;
  use: string;
};

const ASSETS: Asset[] = [
  {
    label: "Mark, color",
    filename: "logo-mark.svg",
    size: "64×64 (scales)",
    format: "SVG",
    use: "Favicon, in-product icon, social avatar background-aware.",
  },
  {
    label: "Mark, monochrome",
    filename: "logo-mono.svg",
    size: "64×64 (scales)",
    format: "SVG",
    use: "Invoices, PDF reports, slide decks in grayscale, iOS pinned tab.",
  },
  {
    label: "Mark, 400px PNG (transparent)",
    filename: "logo-mark-400.png",
    size: "400×400",
    format: "PNG",
    use: "Slack avatar, X profile picture, anywhere alpha is allowed.",
  },
  {
    label: "Wordmark, horizontal lockup",
    filename: "logo-wordmark.svg",
    size: "240×64 (scales)",
    format: "SVG",
    use: "Site header, deck title bars, email signatures, footer of reports.",
  },
  {
    label: "LinkedIn page avatar",
    filename: "linkedin-avatar-400.png",
    size: "400×400",
    format: "PNG",
    use: "LinkedIn company-page profile picture (upload directly).",
  },
  {
    label: "LinkedIn page cover",
    filename: "linkedin-cover.png",
    size: "1128×191",
    format: "PNG",
    use: "LinkedIn company-page cover (upload directly).",
  },
  {
    label: "LinkedIn page cover at 2x (retina)",
    filename: "linkedin-cover-2x.png",
    size: "2256×382",
    format: "PNG",
    use: "Use this one. LinkedIn downsamples it crisply for retina screens.",
  },
];

const COLORS: { name: string; hex: string; use: string; light: boolean }[] = [
  { name: "Bg", hex: "#0a0f1a", use: "Page canvas (dark)", light: false },
  { name: "Surface", hex: "#111a2b", use: "Cards, panels", light: false },
  { name: "Fg / Ink", hex: "#e9f0f8", use: "Primary text on dark", light: true },
  { name: "Teal", hex: "#2dd4bf", use: "Brand accent · keel · links · CTAs", light: true },
  { name: "Navy (action)", hex: "#0d9488", use: "Primary action fill", light: true },
  { name: "Coral", hex: "#ff6b54", use: "Warnings · win-point · over-discounted", light: true },
  { name: "Amber", hex: "#f0b34a", use: "Secondary alert · 'phase 3' label", light: true },
  { name: "Muted", hex: "#8ea3bd", use: "Secondary text", light: false },
  { name: "Mist", hex: "#1f2c43", use: "Borders, dividers", light: false },
];

export default function BrandPage() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-3xl font-bold text-fg">Brand kit</h1>
      <p className="mt-2 max-w-2xl text-sm text-muted">
        Logos, marks, social covers. Pricekeel is a B2B SaaS pricing-decision
        product; we ask that you use these assets to refer to Pricekeel
        accurately and not to imply endorsement.
      </p>

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-fg">Mark</h2>
        <p className="mt-1 text-sm text-muted">
          A stylised ship&rsquo;s keel beneath the waterline. Structure
          that keeps the surface even. The keel is the brand; the
          waterline is the quiet horizon above it.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-mist bg-surface p-6 text-center">
            <div className="flex h-28 items-center justify-center">
              {/* color on dark */}
              <svg width="80" height="80" viewBox="0 0 64 64" aria-label="Pricekeel mark">
                <line x1="10" y1="26" x2="54" y2="26" stroke="#e9f0f8" strokeWidth="3" strokeLinecap="round" opacity="0.88" />
                <path d="M 14 26 Q 34 60 50 26" fill="none" stroke="#2dd4bf" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="text-xs text-muted">color · on dark</div>
          </div>
          <div className="rounded-xl border border-mist bg-fg p-6 text-center">
            <div className="flex h-28 items-center justify-center text-bg">
              {/* monochrome on light */}
              <svg width="80" height="80" viewBox="0 0 64 64" aria-label="Pricekeel mark (mono)">
                <line x1="10" y1="26" x2="54" y2="26" stroke="currentColor" strokeWidth="3" strokeLinecap="round" opacity="0.55" />
                <path d="M 14 26 Q 34 60 50 26" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="text-xs text-muted">monochrome · on light</div>
          </div>
          <div className="rounded-xl border border-mist bg-fg p-6 text-center">
            <div className="flex h-28 items-center justify-center text-teal">
              {/* color on light */}
              <svg width="80" height="80" viewBox="0 0 64 64" aria-label="Pricekeel mark (color on light)">
                <line x1="10" y1="26" x2="54" y2="26" stroke="#0a0f1a" strokeWidth="3" strokeLinecap="round" opacity="0.88" />
                <path d="M 14 26 Q 34 60 50 26" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="text-xs text-muted">color · on light</div>
          </div>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-fg">Wordmark</h2>
        <div className="mt-4 rounded-xl border border-mist bg-surface p-8">
          <div className="text-5xl font-extrabold tracking-tight">
            <span className="text-fg">Price</span>
            <span className="text-teal">keel</span>
          </div>
          <p className="mt-3 text-xs text-muted">
            Inter ExtraBold · letter-spacing -1% · &ldquo;Price&rdquo; in
            primary text, &ldquo;keel&rdquo; in brand teal.
          </p>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-fg">Colors</h2>
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {COLORS.map((c) => (
            <div key={c.hex} className="rounded-lg border border-mist bg-surface p-3">
              <div
                className="h-10 w-full rounded"
                style={{ background: c.hex }}
              />
              <div className="mt-2 text-sm font-semibold text-fg">{c.name}</div>
              <div className="font-mono text-xs text-muted">{c.hex}</div>
              <div className="mt-1 text-[11px] text-muted">{c.use}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-fg">Downloads</h2>
        <div className="mt-4 overflow-x-auto rounded-xl border border-mist">
          <table className="w-full border-collapse text-sm">
            <thead className="bg-surface-2 text-left text-xs uppercase tracking-wider text-muted">
              <tr>
                <th className="px-3 py-2 font-semibold">Asset</th>
                <th className="px-3 py-2 font-semibold">Size</th>
                <th className="px-3 py-2 font-semibold">Format</th>
                <th className="px-3 py-2 font-semibold">When to use</th>
                <th className="px-3 py-2 font-semibold">Download</th>
              </tr>
            </thead>
            <tbody>
              {ASSETS.map((a) => (
                <tr key={a.filename} className="border-t border-mist align-top">
                  <td className="px-3 py-2 font-medium text-fg">{a.label}</td>
                  <td className="px-3 py-2 text-muted">{a.size}</td>
                  <td className="px-3 py-2 text-muted">{a.format}</td>
                  <td className="px-3 py-2 text-muted">{a.use}</td>
                  <td className="px-3 py-2">
                    <a
                      className="text-teal underline"
                      href={`/brand/${a.filename}`}
                      download
                    >
                      {a.filename}
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-fg">Use guidelines</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
          <li>Keep clear-space around the mark equal to at least the height of the waterline stroke.</li>
          <li>Do not recolor the keel curve to any color other than the brand teal (or the brand monochrome).</li>
          <li>Do not stretch, skew, rotate, or add drop-shadow to the mark.</li>
          <li>Pair the wordmark only with the Inter type system or a close geometric sans.</li>
          <li>Do not use the mark on a busy photographic background without a solid scrim behind it.</li>
        </ul>
      </section>
    </main>
  );
}
