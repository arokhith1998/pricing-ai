import { getDeals, getModel, type Deal, type ModelInfo } from "@/lib/api";
import { pct } from "@/lib/format";
import Reveal from "@/components/Reveal";
import ApiError from "@/components/ApiError";
import GuidanceClient from "@/components/GuidanceClient";
import PageGuide from "@/components/PageGuide";
import NextStep from "@/components/NextStep";

export const dynamic = "force-dynamic";

export default async function GuidancePage() {
  let deals: Deal[];
  let model: ModelInfo;
  try {
    [deals, model] = await Promise.all([getDeals(), getModel()]);
  } catch {
    return <ApiError />;
  }

  const m = model.metrics;

  return (
    <main className="mx-auto max-w-6xl space-y-8 px-6 py-8">
      <Reveal>
        <h1 className="text-2xl font-bold text-fg">Guidance</h1>
        <p className="mt-1 max-w-2xl text-slate">
          For a given deal, the discount that earns the most expected value. The
          model learns from your closed deals, using only what is known at quote
          time. It is decision support for a human, not an autopilot.
        </p>
      </Reveal>

      <Reveal delay={0.04}>
        <PageGuide
          eyebrow="Reading this page"
          title="One deal at a time. Pick from the dropdown to switch."
          body="The model uses only features known at quote time and is trained without outcome leakage. The recommendation maximizes expected value: P(win) × list × (1 − discount)."
          bullets={[
            "The headline says what to give and what it is worth: current vs recommended discount, expected value gain.",
            "Top factors say WHY this deal looks more or less winnable, in plain language.",
            "Model quality (ranking + calibration) is at the bottom for the analyst.",
          ]}
        />
      </Reveal>

      <Reveal delay={0.05}>
        <GuidanceClient deals={deals} />
      </Reveal>

      <Reveal delay={0.05}>
        <section className="rounded-xl border border-mist bg-surface p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-fg">Model quality</h2>
          <p className="mt-1 text-sm text-slate">
            How well the win-probability model separates and calibrates on a
            held-out test set. Calibration matters most: the predicted win chance
            should match reality.
          </p>
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="rounded-lg border border-teal/30 bg-surface-2 p-3">
              <div className="text-sm font-medium text-teal">
                Calibration ← lead with this
              </div>
              <div className="mt-1 text-xl font-bold tabular-nums text-fg">
                {pct(m.mean_pred)} vs {pct(m.base_rate)}
              </div>
              <div className="text-xs text-slate">
                predicted vs actual win rate (the only thing finance cares about)
              </div>
            </div>
            <div>
              <div className="text-sm text-slate">Ranking quality</div>
              <div className="text-xl font-bold tabular-nums text-fg">
                {m.auc.toFixed(2)}
              </div>
              <div className="text-xs text-slate">
                area under ROC curve · capped by irreducible noise
              </div>
            </div>
            <div>
              <div className="text-sm text-slate">Brier score</div>
              <div className="text-xl font-bold tabular-nums text-fg">
                {m.brier.toFixed(3)}
              </div>
              <div className="text-xs text-slate">lower is better</div>
            </div>
            <div>
              <div className="text-sm text-slate">Trained on</div>
              <div className="text-xl font-bold tabular-nums text-fg">
                {m.n_train.toLocaleString()}
              </div>
              <div className="text-xs text-slate">deals ({m.n_test.toLocaleString()} held out)</div>
            </div>
          </div>
        </section>
      </Reveal>

      <Reveal delay={0.05}>
        <NextStep
          href="/upload"
          title="Run it on your data"
          body="Upload a CSV or Excel of your closed deals. Mapping is local; data is processed in memory and not stored."
        />
      </Reveal>
    </main>
  );
}
