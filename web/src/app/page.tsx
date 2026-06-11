import Link from "next/link";
import Reveal from "@/components/Reveal";
import HeroDemo from "@/components/HeroDemo";
import DiagnosticPreview from "@/components/DiagnosticPreview";
import {
  CTA, SLOTS, hero, useCases, midCta, proof, howItWorks, outcomes, trust, close,
} from "@content/landing";

// One idea per viewport. One CTA, repeated verbatim. Outcome numbers, not
// adjectives. Whitespace is the design (aqqrue.com flow benchmark, structure
// only). Static marketing landing, no API dependency at request time.
export const dynamic = "force-static";

// The single call-to-action. Identical label + destination everywhere.
function Cta({ size = "lg" }: { size?: "lg" | "md" }) {
  return (
    <Link
      href={CTA.href}
      className={`inline-flex items-center justify-center rounded-full bg-teal font-semibold text-bg transition hover:brightness-110 ${
        size === "lg" ? "px-7 py-3.5 text-base" : "px-5 py-2.5 text-sm"
      }`}
    >
      {CTA.label}
    </Link>
  );
}

// One short scroll-triggered glyph per use-case card (teal stroke, the only
// accent above the fold besides the CTA).
function UseCaseGlyph({ kind }: { kind: number }) {
  const common = {
    width: 40, height: 40, viewBox: "0 0 40 40", fill: "none",
    stroke: "currentColor", strokeWidth: 2,
    strokeLinecap: "round" as const, strokeLinejoin: "round" as const,
    className: "text-teal",
  };
  if (kind === 0) // falling realization line
    return <svg {...common}><path d="M4 10 L14 14 L22 26 L36 32" /><path d="M30 32 h6 v-6" /></svg>;
  if (kind === 1) // saturating win curve
    return <svg {...common}><path d="M4 32 C12 32 14 12 22 11 C30 10 32 10 36 10" /><path d="M4 32 h32" opacity="0.35" /></svg>;
  if (kind === 2) // quarter-end spike bars
    return <svg {...common}><path d="M6 30 v-6 M14 30 v-10 M22 30 v-7 M30 30 v-18" /><path d="M4 30 h30" opacity="0.35" /></svg>;
  // ranked list
  return <svg {...common}><path d="M8 12 h24 M8 20 h18 M8 28 h12" /></svg>;
}

function Section({
  children, className = "", id,
}: { children: React.ReactNode; className?: string; id?: string }) {
  return (
    <section id={id} className={`mx-auto max-w-5xl px-6 ${className}`}>{children}</section>
  );
}

export default function Landing() {
  return (
    <main className="pb-12">
      {/* 1. Hero — keep the headline; one-line subhead; product in motion ---- */}
      <Section className="pt-16 pb-24 text-center sm:pt-24">
        <Reveal>
          <h1 className="mx-auto max-w-4xl text-balance font-extrabold leading-[1.05] tracking-tight text-fg text-[clamp(2.75rem,7vw,5.25rem)]">
            {hero.headline}
          </h1>
          <p className="mx-auto mt-6 max-w-[34rem] text-lg leading-relaxed text-muted">
            {hero.subhead}
          </p>
          <div className="mt-9 flex justify-center">
            <Cta />
          </div>
        </Reveal>
        <Reveal delay={0.08} className="mt-14">
          <div className="mx-auto max-w-3xl">
            <HeroDemo />
          </div>
        </Reveal>
      </Section>

      {/* 2. Use-case cards (4) — capability + customer vocabulary ------------- */}
      <Section className="py-20">
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          {useCases.map((u, i) => (
            <Reveal key={u.name} delay={i * 0.06}>
              <div className="h-full rounded-2xl border border-border bg-surface p-6">
                <UseCaseGlyph kind={i} />
                <h3 className="mt-4 text-lg font-semibold text-fg">{u.name}</h3>
                <p className="mt-2 text-[15px] leading-relaxed text-muted">{u.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </Section>

      {/* 3. Mid-page CTA band ------------------------------------------------- */}
      <Section className="py-16">
        <Reveal>
          <div className="flex flex-col items-center gap-6 rounded-2xl border border-border bg-surface-2 px-6 py-12 text-center">
            <p className="max-w-xl text-2xl font-semibold text-fg">{midCta}</p>
            <Cta />
          </div>
        </Reveal>
      </Section>

      {/* 4. Proof — the live sample report, clearly labeled synthetic -------- */}
      <Section className="py-20">
        <Reveal className="text-center">
          <h2 className="text-3xl font-bold tracking-tight text-fg">{proof.title}</h2>
          <p className="mx-auto mt-3 max-w-xl text-muted">{proof.subtitle}</p>
        </Reveal>
        <Reveal delay={0.06} className="mt-10">
          <DiagnosticPreview />
        </Reveal>
        <Reveal delay={0.1} className="mt-6 text-center">
          <Link href="/sample" className="text-sm font-medium text-teal underline-offset-4 hover:underline">
            Explore the full sample report →
          </Link>
        </Reveal>
      </Section>

      {/* 5. How it works — 3 steps ------------------------------------------- */}
      <Section id="how-it-works" className="scroll-mt-24 py-20">
        <Reveal className="text-center">
          <h2 className="text-3xl font-bold tracking-tight text-fg">How it works</h2>
        </Reveal>
        <div className="mt-10 grid grid-cols-1 gap-5 md:grid-cols-3">
          {howItWorks.map((s, i) => (
            <Reveal key={s.step} delay={i * 0.06}>
              <div className="h-full rounded-2xl border border-border bg-surface p-6">
                <div className="font-mono text-sm text-teal">{s.step}</div>
                <h3 className="mt-3 text-lg font-semibold text-fg">{s.title}</h3>
                <p className="mt-2 text-[15px] leading-relaxed text-muted">{s.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </Section>

      {/* 6. Outcome numbers — one row, three, accent on the figures ---------- */}
      <Section className="py-20">
        <Reveal className="text-center">
          <p className="text-sm uppercase tracking-wider text-muted">{outcomes.caption}</p>
          <div className="mt-8 grid grid-cols-1 gap-8 sm:grid-cols-3">
            {outcomes.stats.map((s) => (
              <div key={s.value}>
                <div className="text-4xl font-extrabold tabular-nums text-teal sm:text-5xl">
                  {s.value}
                </div>
                <div className="mx-auto mt-2 max-w-[14rem] text-sm text-muted">{s.label}</div>
              </div>
            ))}
          </div>
        </Reveal>
      </Section>

      {/* 7. Trust block — honest, no fake badges ----------------------------- */}
      <Section className="py-20">
        <Reveal className="text-center">
          <h2 className="text-3xl font-bold tracking-tight text-fg">What you can count on</h2>
        </Reveal>
        <div className="mt-10 grid grid-cols-1 gap-5 sm:grid-cols-2">
          {trust.map((t, i) => (
            <Reveal key={t.title} delay={i * 0.05}>
              <div className="h-full rounded-2xl border border-border bg-surface p-6">
                <h3 className="text-base font-semibold text-fg">{t.title}</h3>
                <p className="mt-2 text-[15px] leading-relaxed text-muted">{t.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
        <Reveal delay={0.1} className="mt-6 text-center text-sm text-muted">
          Read the{" "}
          <Link href="/privacy" className="text-teal underline-offset-4 hover:underline">Privacy Policy</Link>{" "}
          and{" "}
          <Link href="/terms" className="text-teal underline-offset-4 hover:underline">Terms of Use</Link>.
        </Reveal>
      </Section>

      {/* 8. Identity + scarcity close ---------------------------------------- */}
      <Section className="py-24 text-center">
        <Reveal>
          <h2 className="mx-auto max-w-2xl text-balance text-3xl font-bold tracking-tight text-fg sm:text-4xl">
            {close.title}
          </h2>
          <p className="mx-auto mt-5 max-w-xl text-lg leading-relaxed text-muted">{close.body}</p>
          <p className="mt-8 text-sm font-medium text-teal">
            Founding cohort: {SLOTS} free diagnostic slots remaining.
          </p>
          <div className="mt-6 flex justify-center">
            <Cta />
          </div>
        </Reveal>
      </Section>
    </main>
  );
}
