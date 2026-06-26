"""Governance loop — persistent decision store, exception verdicts, weekly digest.

The decision log is the product's system-of-record moat: every copilot
decision and every discount-exception request is appended here with the
deterministic math that backed it. Storage is Neon/Postgres (psycopg) when
DATABASE_URL is set, with an in-memory fallback for dev and tests. A failed
database call never fails the request: we log, fall back to memory, and keep
serving.

Honesty rules (same as pricing/copilot.py): every number in a verdict or
digest is deterministic — read off the win-probability model's EV curve or
the diagnostic aggregates. No LLM is involved anywhere in this module, the
digest carries the correlational caveat, and no generated text contains an
em dash (house style).

Percent convention (the API surface): discount and realization figures are
percent 0-100 — requested_discount_pct=22.5 means a 22.5 percent discount,
floor_pct defaults to 15.0. Win probabilities stay 0-1 fractions, EV deltas
are dollars. Internal model math stays in 0-1 fractions; conversion happens
at this module's boundary.
"""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

from pricing import model
from pricing.schema import DEFAULT_POLICY_THRESHOLD

logger = logging.getLogger("pricekeel.governance")

_TABLE = "decision_log"
_CONNECT_TIMEOUT_S = 5  # libpq connect_timeout is whole seconds

# The win-probability model sweeps discounts on a 0..40% grid
# (model.recommend_discount). Requests outside it cannot be scored honestly.
# Percent 0-100, like the rest of the API surface.
EXCEPTION_MAX_PCT = 40.0

# Policy floor on the API surface, percent 0-100. DEFAULT_POLICY_THRESHOLD is
# the engine-internal 0-1 fraction (0.15).
FLOOR_PCT_DEFAULT = DEFAULT_POLICY_THRESHOLD * 100.0

DECISION_KINDS = ("copilot", "exception")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(s: str) -> Optional[datetime]:
    """Lenient ISO-8601 parse (Postgres may emit 'Z' or '+00:00')."""
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _db_url() -> Optional[str]:
    """The Neon/Postgres connection string when set; read at call time so
    tests and Render env changes take effect without re-import (same
    convention as the API perimeter)."""
    url = os.environ.get("DATABASE_URL", "").strip()
    return url or None


def _row_out(row: dict) -> dict:
    """Normalize a DB row for the API surface: uuid -> str, datetime -> ISO."""
    out = dict(row)
    if "id" in out:
        out["id"] = str(out["id"])
    created = out.get("created_at")
    if hasattr(created, "isoformat"):
        out["created_at"] = created.isoformat()
    return out


class DecisionStore:
    """Append-only decision log: Neon/Postgres-backed, memory-fallback.

    Rows mirror the `decision_log` table in neon/schema.sql:
      id, customer_ref, kind, deal_id, payload (dict), decision,
      justification, requested_by, created_at (ISO-8601 string).

    Memory holds rows written while the database was unset OR unreachable, so
    reads merge both sources — a transient outage loses nothing for the
    lifetime of the process.
    """

    def __init__(self) -> None:
        self._memory: list[dict] = []
        self._lock = threading.Lock()

    # -- test hook ----------------------------------------------------------
    def reset_memory(self) -> None:
        with self._lock:
            self._memory.clear()

    # -- write ---------------------------------------------------------------
    def insert(self, *, kind: str, deal_id: str = "", payload: dict | None = None,
               decision: str = "", justification: str = "", requested_by: str = "",
               customer_ref: str = "default") -> dict:
        """Append one decision. Returns the stored row (with id, created_at).

        Never raises on storage failure: a database error degrades to the
        in-memory log so the caller's request still succeeds.

        The returned row carries a transient `persisted` flag (Finding 5):
        True when the write reached the database durably, False when it landed
        in the memory fallback (database unset or unreachable). The flag is for
        the caller's response only; it is not part of the stored row.
        """
        if kind not in DECISION_KINDS:
            raise ValueError(f"kind must be one of {DECISION_KINDS}, got {kind!r}")
        body = {
            "customer_ref": customer_ref,
            "kind": kind,
            "deal_id": deal_id,
            "payload": payload or {},
            "decision": decision,
            "justification": justification,
            "requested_by": requested_by,
        }
        url = _db_url()
        if url is not None:
            try:
                with psycopg.connect(url, connect_timeout=_CONNECT_TIMEOUT_S) as conn:
                    with conn.cursor(row_factory=dict_row) as cur:
                        cur.execute(
                            f"insert into {_TABLE} "
                            "(customer_ref, kind, deal_id, payload, decision, "
                            "justification, requested_by) "
                            "values (%s, %s, %s, %s, %s, %s, %s) returning *",
                            (body["customer_ref"], body["kind"], body["deal_id"],
                             Json(body["payload"]), body["decision"],
                             body["justification"], body["requested_by"]),
                        )
                        row = cur.fetchone()
                if row:
                    return {**_row_out(row), "persisted": True}
                raise ValueError("insert returned no row")
            except Exception as exc:  # noqa: BLE001 — degrade, never 500
                logger.warning("decision_log insert fell back to memory: %s", exc)
        # persisted=False: this is the memory fallback, not durable storage.
        # The flag lives on the stored row too (harmless: readers select the
        # fields they need) so callers that mutate the returned dict in tests
        # keep affecting the stored row by identity.
        row = {**body, "id": str(uuid.uuid4()),
               "created_at": _now_utc().isoformat(), "persisted": False}
        with self._lock:
            self._memory.append(row)
        return row

    # -- read ----------------------------------------------------------------
    def list(self, *, kind: str | None = None, session_id: str | None = None,
             since: datetime | None = None, limit: int = 200,
             newest_first: bool = True,
             customer_ref: str = "default") -> list[dict]:
        """Rows matching the filters, database and memory merged the same way.

        Tenant-scoped: only rows for `customer_ref` are returned (Finding 3).
        One customer's decision log is invisible to another.
        """
        rows: list[dict] = []
        url = _db_url()
        if url is not None:
            clauses = ["customer_ref = %s"]
            vals: list[Any] = [customer_ref]
            if kind:
                clauses.append("kind = %s")
                vals.append(kind)
            if session_id is not None:
                # payload->>'session_id': extract the JSON field as text.
                clauses.append("payload->>'session_id' = %s")
                vals.append(session_id)
            if since is not None:
                clauses.append("created_at >= %s")
                vals.append(since)
            where = " and ".join(clauses)
            order = "desc" if newest_first else "asc"
            query = (f"select * from {_TABLE} where {where} "
                     f"order by created_at {order} limit %s")
            vals.append(limit)
            try:
                with psycopg.connect(url, connect_timeout=_CONNECT_TIMEOUT_S) as conn:
                    with conn.cursor(row_factory=dict_row) as cur:
                        cur.execute(query, vals)
                        fetched = cur.fetchall()
                rows = [_row_out(r) for r in fetched]
            except Exception as exc:  # noqa: BLE001
                logger.warning("decision_log read fell back to memory: %s", exc)
        # Memory rows: everything written with no DB configured or during an outage.
        with self._lock:
            mem = [r for r in self._memory
                   if self._matches(r, kind, session_id, since, customer_ref)]
        seen = {r.get("id") for r in rows}
        rows.extend(r for r in mem if r.get("id") not in seen)
        rows.sort(key=lambda r: (_parse_iso(r.get("created_at", ""))
                                 or datetime.min.replace(tzinfo=timezone.utc)),
                  reverse=newest_first)
        return rows[:limit]

    @staticmethod
    def _matches(row: dict, kind: str | None, session_id: str | None,
                 since: datetime | None, customer_ref: str = "default") -> bool:
        if row.get("customer_ref", "default") != customer_ref:
            return False
        if kind and row.get("kind") != kind:
            return False
        if session_id is not None:
            if (row.get("payload") or {}).get("session_id") != session_id:
                return False
        if since is not None:
            created = _parse_iso(row.get("created_at", ""))
            if created is None or created < since:
                return False
        return True


# Module-level singleton the API uses. Tests reset via STORE.reset_memory().
STORE = DecisionStore()


# ---------------------------------------------------------------------------
# Copilot decision log — same request/response shapes the existing web UI
# consumes from /copilot/log and /copilot/decisions, now persisted.


def log_copilot_decision(session_id: str, qid: str, *,
                         surfaced: list[str] | None = None,
                         accepted: list[str] | None = None,
                         rejected: list[str] | None = None,
                         note: str = "",
                         customer_ref: str = "default") -> dict:
    """Persist one copilot decision; returns the legacy decision dict shape."""
    d = {
        "ts": time.time(),
        "session_id": session_id,
        "qid": qid,
        "opportunities_surfaced": list(surfaced or []),
        "opportunities_accepted": list(accepted or []),
        "opportunities_rejected": list(rejected or []),
        "note": note,
    }
    STORE.insert(kind="copilot", payload=d, decision=qid, justification=note,
                 customer_ref=customer_ref)
    return d


def copilot_decisions(session_id: str, *,
                      customer_ref: str = "default") -> list[dict]:
    """All decisions for a session, oldest first (legacy contract), scoped to
    the customer."""
    rows = STORE.list(kind="copilot", session_id=session_id,
                      newest_first=False, limit=500, customer_ref=customer_ref)
    return [r.get("payload") or {} for r in rows]


# ---------------------------------------------------------------------------
# Exception verdict — deterministic, from the same EV curve /recommend uses.


def exception_verdict(tm: "model.TrainedModel", X_row, list_acv: float,
                      requested_pct: float,
                      floor_pct: float = FLOOR_PCT_DEFAULT) -> dict:
    """Score a requested discount against the deal's own EV curve.

    Percent convention: `requested_pct` and `floor_pct` come in as percent
    0-100 (22.5 means a 22.5 percent discount), and the *_pct fields in the
    returned verdict are percent 0-100 too. Win probabilities are 0-1
    fractions. `ev_delta_vs_recommended` is dollars, EV(requested) minus
    EV(recommended); it is never positive because the recommended discount
    maximizes expected ACV on the sweep.

    Reuses model.recommend_discount (the /guidance / /recommend math) with
    the requested discount substituted as the deal's current discount, so
    "EV at requested" and "EV at recommended" come off the exact same sweep
    (nearest grid point, same as /recommend's win_prob_at_current). Pure
    function of (model, deal row, list ACV, requested discount, floor).
    No LLM; rationale is one plain sentence built from the numbers.
    """
    requested = float(requested_pct)
    req_frac = requested / 100.0
    row = X_row.copy()
    row["discount_pct"] = req_frac
    rec = model.recommend_discount(tm, row, float(list_acv))

    curve = rec["curve"]
    req_row = curve.iloc[(curve["discount"] - req_frac).abs().argmin()]

    recommended = float(rec["recommended_discount"]) * 100.0
    win_req = float(req_row["win_prob"])
    win_rec = float(rec["win_prob_at_rec"])
    # EV(requested) - EV(recommended). <= 0 by construction: the recommended
    # discount maximizes expected ACV on the sweep.
    ev_delta = float(rec["expected_acv_at_current"] - rec["expected_acv_at_rec"])
    below_floor = requested > float(floor_pct)

    rationale = (
        f"Requested discount {requested:.1f} percent "
        f"{'exceeds' if below_floor else 'is within'} the "
        f"{float(floor_pct):g} percent floor"
    )
    if abs(requested - recommended) < 0.5:
        rationale += (
            f" and matches the engine's recommended discount of "
            f"{recommended:.1f} percent."
        )
    elif abs(ev_delta) < 0.5:
        rationale += (
            f"; the engine recommends {recommended:.1f} percent, with win "
            f"probability {win_rec * 100:.0f} percent at the recommendation "
            f"versus {win_req * 100:.0f} percent at the request and "
            f"essentially the same expected deal value."
        )
    else:
        rationale += (
            f"; the engine recommends {recommended:.1f} percent, where win "
            f"probability is {win_rec * 100:.0f} percent versus "
            f"{win_req * 100:.0f} percent at the request and expected deal "
            f"value is ${abs(ev_delta):,.0f} higher."
        )

    return {
        "requested_pct": requested,
        "recommended_pct": recommended,
        "floor_pct": float(floor_pct),
        "below_floor": bool(below_floor),
        "ev_delta_vs_recommended": ev_delta,
        "win_prob_at_requested": win_req,
        "win_prob_at_recommended": win_rec,
        "rationale": rationale,
    }


# ---------------------------------------------------------------------------
# Weekly digest — deterministic aggregation of the decision log + the loaded
# book's diagnostic aggregates. No row-level customer data beyond what was
# explicitly logged as decisions.


def build_digest(*, analysis: dict | None, store: DecisionStore | None = None,
                 customer: str = "default", window_days: int = 7,
                 floor_pct: float = FLOOR_PCT_DEFAULT) -> dict:
    """Assemble the digest payload for GET /digest.

    `analysis` is the diagnostic result dict (pricing.diagnostic.run) for the
    currently loaded book, or None when no book is loaded — then the
    realization stats are null and the digest covers the log alone.

    Percent convention matches /exceptions: `floor_pct` and the
    `realization_pct` stat are percent 0-100; the segment-excess stat is
    dollars.
    """
    store = store or STORE
    now = _now_utc()
    since = now - timedelta(days=window_days)
    # Tenant-scoped: the digest only sees this customer's decision log.
    entries = store.list(since=since, limit=1000, customer_ref=customer)

    exceptions = [e for e in entries if e.get("kind") == "exception"]
    below = [e for e in exceptions
             if ((e.get("payload") or {}).get("verdict") or {}).get("below_floor")]
    copilot_n = sum(1 for e in entries if e.get("kind") == "copilot")

    realization_pct: float | None = None
    excess_seg: float | None = None
    reference_pct: float | None = None
    if analysis is not None:
        ov = analysis.get("overview") or {}
        lk = analysis.get("leakage") or {}
        if ov.get("price_realization_won") is not None:
            realization_pct = float(ov["price_realization_won"]) * 100.0
        if lk.get("excess_vs_segment_reference_won") is not None:
            excess_seg = float(lk["excess_vs_segment_reference_won"])
        if lk.get("reference_threshold") is not None:
            reference_pct = float(lk["reference_threshold"]) * 100.0

    n_exc, n_below = len(exceptions), len(below)
    headline = (
        f"{n_exc} exception request{'s' if n_exc != 1 else ''} this week, "
        f"{n_below} below the {float(floor_pct):g} percent floor"
    )
    headline += (f"; realization {realization_pct:.1f} percent."
                 if realization_pct is not None else ".")

    lines: list[str] = [
        f"{n_exc} exception request{'s' if n_exc != 1 else ''} and "
        f"{copilot_n} copilot decision{'s' if copilot_n != 1 else ''} were "
        f"logged in the last {window_days} days.",
    ]
    if below:
        biggest = max(
            below,
            key=lambda e: float((e.get("payload") or {})
                                .get("requested_discount_pct") or 0.0),
        )
        bp = biggest.get("payload") or {}
        pct = float(bp.get("requested_discount_pct") or 0.0)
        who = str(bp.get("requested_by") or "").strip()
        line = (f"Largest below-floor request: {pct:.1f} percent on deal "
                f"{bp.get('deal_id', biggest.get('deal_id', ''))}")
        if who:
            line += f", requested by {who}"
        lines.append(line + ".")
    elif n_exc:
        lines.append("No request exceeded the policy floor this week.")
    else:
        lines.append("No exception requests were logged this week.")

    if realization_pct is not None:
        line = (f"Price realization on won deals stands at "
                f"{realization_pct:.1f} percent")
        if excess_seg is not None:
            line += (f", with ${excess_seg:,.0f} of discount sitting above "
                     f"each segment's own reference")
        lines.append(line + ".")
    if reference_pct is not None:
        lines.append(
            f"Reminder: the win curve plateaus near {reference_pct:g} "
            f"percent. Historically, discounts past that point did not buy "
            f"meaningfully more wins. That relationship is correlational, "
            f"not causal."
        )
    if analysis is None:
        lines.append("No deal book is loaded, so realization and win-point "
                     "context are omitted from this digest.")

    return {
        "customer": customer,
        "generated_at": now.isoformat(),
        "window_days": window_days,
        "headline": headline,
        "lines": lines[:6],
        "stats": {
            "exceptions_total": n_exc,
            "exceptions_below_floor": n_below,
            "copilot_decisions": copilot_n,
            "realization_pct": realization_pct,
            "excess_vs_segment_reference": excess_seg,
        },
    }
