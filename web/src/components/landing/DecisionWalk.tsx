"use client";

// The walk: one discount exception in four steps (Request, Evidence, Decision,
// Outcome). Safe by default, same pattern as Reveal.tsx after the 2026-09-27
// empty-viewport bug:
//  - Server render, first paint, no JavaScript, below lg and under
//    prefers-reduced-motion: the four steps are stacked, each with its own
//    panel, all fully visible. Nothing is hidden or transformed.
//  - Only after hydration, at lg and above and with motion allowed, the walk is
//    "armed": steps scroll in the left column while one sticky panel on the
//    right follows the step in view. Arming changes layout, never content.
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import type { MutableRefObject, ReactNode } from "react";
import { Card, StatusIcons, StatusPill, SyntheticTag } from "@/components/ui";
import type { DecisionRecord } from "@/lib/landing-sample";
import { ciText, Field, money, pct, WinBar } from "./parts";

export type WalkStep = { id: string; name: string; title: string; copy: string };

export function buildSteps(r: DecisionRecord): WalkStep[] {
  return [
    {
      id: "request",
      name: "Request",
      title: `An AE asks for ${pct(r.requestedDiscount, 0)} off.`,
      copy: `A ${money(r.listAcv)} ${r.segment} deal${r.quarterEnd ? " at quarter end" : ""}${r.competitorPresent ? ", with a competitor on the opportunity" : ""}. The record keeps the terms exactly as requested.`,
    },
    {
      id: "evidence",
      name: "Evidence",
      title: "The request meets the book.",
      copy: `Win rates by discount band, with their confidence intervals, set against the ${r.segment} segment's reference band. Method named: ${r.method.toLowerCase()}.`,
    },
    {
      id: "decision",
      name: "Decision",
      title: "A person chooses.",
      copy: "Accept the reference or override it with a written reason. The person decides. The product shows the evidence and writes down what was decided.",
    },
    {
      id: "outcome",
      name: "Outcome",
      title: "What the synthetic book recorded.",
      copy: "Not a forecast. This is the result the synthetic book holds for this deal, shown so the decision can be read against what happened.",
    },
  ];
}

function PanelFrame({ step, children }: { step: WalkStep; children: ReactNode }) {
  return (
    <Card tone="card">
      <p className="pk-eyebrow m-0">{step.name}</p>
      <div className="mt-4">{children}</div>
    </Card>
  );
}

const CHOICES = [
  { label: "Accept the reference", picked: false },
  { label: "Override, with a written reason", picked: true },
];

export function StepPanel({ step, record: r }: { step: WalkStep; record: DecisionRecord }) {
  switch (step.id) {
    case "request":
      return (
        <PanelFrame step={step}>
          <dl className="m-0 grid grid-cols-2 gap-x-4 gap-y-3">
            <Field label="Opportunity" mono>
              {r.opportunityId}
            </Field>
            <Field label="Segment">{r.segment}</Field>
            <Field label="List value">{money(r.listAcv)}</Field>
            <Field label="Requested discount">{pct(r.requestedDiscount)}</Field>
          </dl>
          {r.quarterEnd || r.competitorPresent ? (
            <p className="pk-small m-0 mt-4 text-muted">
              Recorded on the opportunity:{" "}
              {[r.quarterEnd ? "quarter-end close" : null, r.competitorPresent ? "competitor present" : null]
                .filter(Boolean)
                .join(", ")}
              .
            </p>
          ) : null}
          <SyntheticTag className="mt-4" />
        </PanelFrame>
      );
    case "evidence":
      return (
        <PanelFrame step={step}>
          {[
            { band: r.requestedBand, label: `Requested, ${r.requestedBand.label} band, all segments`, emphasis: false },
            {
              band: r.referenceBand,
              label: `${r.segment} reference, ${r.referenceBandLabel} band`,
              emphasis: true,
            },
          ].map(({ band, label, emphasis }) => (
            <div key={label} className="mb-4">
              <div className="flex items-baseline justify-between gap-3">
                <p className="pk-small m-0 text-muted">{label}</p>
                <p className="m-0 font-semibold tabular-nums text-fg">{pct(band.winRate)} win rate, all segments</p>
              </div>
              <div className="mt-2">
                <WinBar band={band} emphasis={emphasis} />
              </div>
              <p className="pk-small m-0 mt-1 text-muted">
                interval {ciText(band)}, {band.deals} deals
              </p>
            </div>
          ))}
          <dl className="m-0 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Method">{r.method}</Field>
            <Field label="Page fingerprint" mono>
              {r.pageFingerprint}
            </Field>
          </dl>
          <SyntheticTag className="mt-4" />
        </PanelFrame>
      );
    case "decision":
      return (
        <PanelFrame step={step}>
          <p className="pk-small m-0 text-muted">A person picks one:</p>
          <ul className="m-0 mt-2 list-none space-y-2 p-0" aria-label="Choices a person has">
            {CHOICES.map((o) => (
              <li
                key={o.label}
                className={`flex min-h-11 items-center justify-between gap-3 rounded-control border px-3 text-small ${
                  o.picked ? "border-teal text-fg" : "border-control text-muted"
                }`}
              >
                <span>{o.label}</span>
                {o.picked ? <span className="pk-micro text-teal">Chosen by a person</span> : null}
              </li>
            ))}
          </ul>
          <div className="pk-surface-inset mt-4 p-3">
            <p className="pk-small m-0 font-semibold text-fg">Log row</p>
            <dl className="pk-mono m-0 mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
              <dt className="text-muted">decided_by</dt>
              <dd className="m-0 text-fg">a person (Deal Desk)</dd>
              <dt className="text-muted">choice</dt>
              <dd className="m-0 text-fg">override</dd>
              <dt className="text-muted">requested</dt>
              <dd className="m-0 text-fg">{pct(r.requestedDiscount)}</dd>
              <dt className="text-muted">page_fingerprint</dt>
              <dd className="m-0 break-all text-fg">{r.pageFingerprint}</dd>
            </dl>
          </div>
          <SyntheticTag variant="illustrative" className="mt-4" />
        </PanelFrame>
      );
    default:
      return (
        <PanelFrame step={step}>
          <StatusPill tone="ok" label="Won in the synthetic book" icon={StatusIcons.ok} />
          <dl className="m-0 mt-4 grid grid-cols-2 gap-x-4 gap-y-3">
            <Field label="Booked">{money(r.bookedAcv)}</Field>
            <Field label="List">{money(r.listAcv)}</Field>
            <Field label="Price realization">{pct(r.priceRealization)}</Field>
            <Field label="Discount taken">{pct(r.requestedDiscount)}</Field>
          </dl>
          <SyntheticTag className="mt-4" />
        </PanelFrame>
      );
  }
}

// --- arming ------------------------------------------------------------------
const ARM_QUERY = "(min-width: 1024px) and (prefers-reduced-motion: no-preference)";

const canMatch = () => typeof window !== "undefined" && typeof window.matchMedia === "function";

function subscribe(onChange: () => void) {
  if (!canMatch()) return () => {};
  const mq = window.matchMedia(ARM_QUERY);
  mq.addEventListener("change", onChange);
  return () => mq.removeEventListener("change", onChange);
}
const getSnapshot = () => canMatch() && window.matchMedia(ARM_QUERY).matches;
// Server and the first client paint: never armed.
const getServerSnapshot = () => false;

export function useArmed(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

// The presentational walk. `armed` is a prop so tests render the stacked,
// unarmed form without the matchMedia subscription.
export function WalkView({
  steps,
  record,
  armed,
  active = 0,
  stepRefs,
}: {
  steps: WalkStep[];
  record: DecisionRecord;
  armed: boolean;
  active?: number;
  stepRefs?: MutableRefObject<Array<HTMLLIElement | null>>;
}) {
  return (
    <div
      className={armed ? "grid grid-cols-[minmax(0,5fr)_minmax(0,6fr)] gap-12" : undefined}
      data-armed={armed}
    >
      <ol className="m-0 list-none space-y-10 p-0" aria-label="One discount exception, four steps">
        {steps.map((s, i) => (
          <li
            key={s.id}
            data-step={s.id}
            ref={(el) => {
              if (stepRefs) stepRefs.current[i] = el;
            }}
            className={
              armed
                ? `flex min-h-[55vh] flex-col justify-center border-l-2 pl-6 transition-colors duration-200 ${i === active ? "border-teal" : "border-border"}`
                : "grid gap-4 md:grid-cols-2 md:gap-8"
            }
          >
            <div>
              <p className="pk-mono m-0 text-teal">
                {String(i + 1).padStart(2, "0")} {s.name}
              </p>
              <h3 className="pk-h3 m-0 mt-2">{s.title}</h3>
              <p className="pk-body m-0 mt-2 max-w-[68ch]">{s.copy}</p>
            </div>
            {armed ? null : <StepPanel step={s} record={record} />}
          </li>
        ))}
      </ol>
      {armed ? (
        <div className="relative">
          <div className="sticky top-28" aria-live="polite">
            <div key={steps[active].id} className="pk-fade-in">
              <StepPanel step={steps[active]} record={record} />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function DecisionWalk({ record }: { record: DecisionRecord }) {
  const steps = buildSteps(record);
  const armed = useArmed();
  const [active, setActive] = useState(0);
  const stepRefs = useRef<Array<HTMLLIElement | null>>([]);

  useEffect(() => {
    if (!armed) return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            const i = stepRefs.current.indexOf(e.target as HTMLLIElement);
            if (i >= 0) setActive(i);
          }
        }
      },
      { rootMargin: "-45% 0px -45% 0px" },
    );
    stepRefs.current.forEach((el) => el && io.observe(el));
    return () => io.disconnect();
  }, [armed]);

  return (
    <WalkView
      steps={steps}
      record={record}
      armed={armed}
      active={armed ? active : 0}
      stepRefs={stepRefs}
    />
  );
}
