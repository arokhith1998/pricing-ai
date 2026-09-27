"""State and payload helpers shared by more than one router.

`api/main.py` used to be one 1400-line module, so every helper below was a
plain module-level function. Splitting main.py into `api/routers/*.py`
created a real hazard the split has to avoid: two routers each defining
their own copy of, say, the trained win-probability model would silently
drift (governance would score a deal against a different model snapshot
than the guidance UI showed). This module is the single source for state
and payload shaping that more than one component needs, so there is exactly
one cache / one shape-conversion, imported everywhere it is used.

Naming: `engine`, `records`, `analysis_payload`, and `diagnostic_payload`
below are unprefixed because this module's whole purpose is to be imported
by other routers; they are the public API. `_load_report_dict` and
`_ENGINE` stay prefixed because nothing outside this file imports them.

Nothing perimeter-specific (rate limiting, the upload-size cap, auth) lives
here; those stay in api/main.py itself. See the note at the top of
api/main.py for why.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np
import pandas as pd

from pricing import model
from pricing.diagnostic import run
from pricing.ingest import ingest

ROOT = Path(__file__).resolve().parents[1]
DEMO_CSV = ROOT / "data" / "synthetic" / "deals.csv"


def records(df) -> list[dict]:
    """DataFrame to JSON-safe records (handles numpy types via to_json)."""
    return json.loads(df.to_json(orient="records"))


def _load_report_dict(rep) -> dict:
    """LoadReport dataclass -> JSON-safe dict, plus its human summary block."""
    d = dataclasses.asdict(rep)
    d["summary"] = rep.summary()
    # Round-trip to flush any stray numpy scalars to plain JSON types.
    return json.loads(json.dumps(d, default=str))


def analysis_payload(res: dict) -> dict:
    """JSON-safe dashboard payload for CSV and live-CRM analyses."""
    return {
        # "What we read from your file": ingest disclosures (duplicates
        # dropped, open deals excluded, encoding, unmapped columns, ...).
        "load_report": _load_report_dict(res["load_report"]),
        "overview": res["overview"],
        "leakage": res["leakage"],
        "reference_discount": res["reference_discount"],
        # Per-value-metric reference cut (list of dicts, already JSON-safe):
        # {value_metric, deals, bands_populated, reference_threshold,
        # reference_band, basis}. Forwarded verbatim from diagnostic.analyze.
        "value_metric_reference": res["value_metric_reference"],
        "quarter_end": res["quarter_end"],
        "governance": res["governance"],
        "trend_by_quarter": records(res["trend_by_quarter"]),
        "segment_win_points": res["segment_win_points"],
        "policy_simulations": res["policy_simulations"],
        "new_vs_renewal": records(res["new_vs_renewal"]),
        "rep_discipline": records(res["rep_discipline"]),
        "win_rate_by_band": records(res["win_rate_by_band"]),
        "realization_by_segment": records(res["realization_by_segment"]),
        "top_leak_deals": records(res["top_leak_deals"]),
        # Optional hierarchy slices: dimension -> list of {dim, deals, list_acv,
        # booked_acv, avg_discount, price_realization}. Empty {} if none present.
        "hierarchy_slices": {
            dim: records(rows) for dim, rows in res["hierarchy_slices"].items()
        },
        # Framework-grounded follow-on signals.
        "packaging_signals": res["packaging_signals"],
        "trade_or_give": res["trade_or_give"],
        "trade_or_give_deals": records(res["trade_or_give_deals"]),
        "quarter_end_deals": records(res["quarter_end_deals"]),
        "packaging_signal_deals": records(res["packaging_signal_deals"]),
        "defended_vs_investigate": res["defended_vs_investigate"],
    }


def diagnostic_payload(csv_path: str, policy: float) -> dict:
    return analysis_payload(run(csv_path, policy_threshold=policy))


# --- Win-probability model + discount guidance (Phase 2 / web M2) ------------
#
# Training the LightGBM model takes ~1s on the demo data, so we train once and
# cache it (keyed on the CSV's mtime). Both the model router (/model, /deals,
# /recommend) and the governance router (/exceptions looks a deal up against
# this same trained model) need it: a second cache here would mean the two
# could silently score against different model snapshots, so this is the one
# place it is built.

_ENGINE: dict = {"mtime": None, "df": None, "tm": None}


def engine() -> tuple[pd.DataFrame, "model.TrainedModel"]:
    """Return (ingested df, trained model), rebuilding if the CSV changed."""
    mtime = DEMO_CSV.stat().st_mtime
    if _ENGINE["mtime"] != mtime:
        df = ingest(str(DEMO_CSV))
        _ENGINE.update(mtime=mtime, df=df, tm=model.train(df))
    return _ENGINE["df"], _ENGINE["tm"]


def in_sample(tm: "model.TrainedModel", df: pd.DataFrame, idx) -> bool:
    """True when deal `idx` was in the training partition, not the holdout
    the model's own metrics were scored on (mle-reviewer, 2026-09-27: the
    demo scores rows it trained on for most of the top /deals). A win
    probability shown for an in-sample row is optimistic relative to one
    genuinely held out; disclosed rather than hidden, and cheaper than a
    second, nested out-of-fold model that would also have to re-derive a
    prediction for every hypothetical discount /recommend sweeps, not only
    the deal's own recorded one.

    `tm.holdout` is a plain boolean array positional in the same row order as
    the `df` it was trained on, so this looks up `idx`'s position, not its
    label, and only ever runs against the one `df` returned alongside `tm` by
    `engine()`.
    """
    if tm.holdout is None:
        return True
    pos = df.index.get_loc(idx)
    return not bool(tm.holdout[pos])


def in_sample_mask(tm: "model.TrainedModel", df: pd.DataFrame, index) -> np.ndarray:
    """Vectorized `in_sample` for a batch of deals (e.g. the /deals list)."""
    if tm.holdout is None:
        return np.ones(len(index), dtype=bool)
    pos = df.index.get_indexer(index)
    return ~tm.holdout[pos]
