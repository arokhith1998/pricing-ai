import { getDeals, getModel, type Deal, type ModelInfo } from "@/lib/api";
import { pct } from "@/lib/format";
import Reveal from "@/components/Reveal";
import ApiError from "@/components/ApiError";
import GuidanceClient from "@/components/GuidanceClient";

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
            <div>
              <div className="text-sm text-slate">Ranking quality</div>
              <div className="text-xl font-bold tabular-nums text-fg">
                {m.auc.toFixed(2)}
              </div>
              <div className="text-xs text-slate">area under ROC curve</div>
            </div>
            <div>
              <div className="text-sm text-slate">Calibration</div>
              <div className="text-xl font-bold tabular-nums text-fg">
                {pct(m.mean_pred)} vs {pct(m.base_rate)}
              </div>
              <div className="text-xs text-slate">predicted vs actual win rate</div>
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
    </main>
  );
}
