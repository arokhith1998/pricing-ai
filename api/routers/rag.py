"""RAG component: /docs/upload, /ask — Ask-your-Pricekeel (Phase 3.0).

Docs + analysis + (optional) web RAG. `MAX_UPLOAD_BYTES`/`_read_capped` (the
perimeter upload cap) stay owned by api/main.py; see that module's note.
The import is deferred to inside the endpoint for the same reason as in
diagnostic.py: api/main.py is still mid-import when this router module is
first loaded.
"""

from __future__ import annotations

import os
import time as _time
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from pricing import docs as docs_mod
from pricing import rag as rag_mod
from api.shared import DEMO_CSV, _diagnostic_payload

router = APIRouter()

# In-memory chunk store keyed by session id. Dev fallback; production should
# move to Neon pgvector keyed to the customer.
#
# This dict is the single piece of process-lifetime state in the API. Without
# any cap it grows on every upload until OOM. Hardening (per the 2026-05-30
# launch-readiness review): per-session chunk cap, total-session cap, TTL,
# and lazy expiry on every read/write. None of this is a substitute for
# moving to Neon pgvector, but it removes the foot-gun for soft launch.

_DOC_STORE: dict[str, tuple[float, list[docs_mod.Chunk]]] = {}
_DOC_STORE_MAX_SESSIONS = int(os.environ.get("PRICEKEEL_DOC_MAX_SESSIONS", "500"))
_DOC_STORE_MAX_CHUNKS_PER_SESSION = int(
    os.environ.get("PRICEKEEL_DOC_MAX_CHUNKS_PER_SESSION", "2000"),
)
_DOC_STORE_TTL_SECONDS = int(
    os.environ.get("PRICEKEEL_DOC_TTL_SECONDS", str(60 * 60 * 4)),  # 4h
)


def _doc_store_expire_old(now: float | None = None) -> None:
    """Drop sessions older than TTL. O(n) — fine at the cap of 500 sessions."""
    now = now if now is not None else _time.time()
    cutoff = now - _DOC_STORE_TTL_SECONDS
    for sid in [s for s, (ts, _) in _DOC_STORE.items() if ts < cutoff]:
        del _DOC_STORE[sid]


def _doc_store_get(sid: str) -> list[docs_mod.Chunk]:
    _doc_store_expire_old()
    entry = _DOC_STORE.get(sid)
    return entry[1] if entry else []


def _doc_store_append(sid: str, new_chunks: list[docs_mod.Chunk]) -> int:
    """Append chunks to a session; enforce per-session and global caps.

    Returns the post-append chunk count. Raises HTTPException(429) if the
    cap is exceeded; raises HTTPException(503) if we are at session capacity
    and this is a *new* session id.
    """
    _doc_store_expire_old()
    existing = _DOC_STORE.get(sid)
    if existing is None and len(_DOC_STORE) >= _DOC_STORE_MAX_SESSIONS:
        raise HTTPException(
            status_code=503,
            detail="Document store is at session capacity; please retry later.",
        )
    existing_chunks = existing[1] if existing else []
    if len(existing_chunks) + len(new_chunks) > _DOC_STORE_MAX_CHUNKS_PER_SESSION:
        raise HTTPException(
            status_code=413,
            detail=(
                f"This session would exceed the chunk cap "
                f"({_DOC_STORE_MAX_CHUNKS_PER_SESSION}). Start a new session "
                "or drop fewer files."
            ),
        )
    merged = existing_chunks + new_chunks
    _DOC_STORE[sid] = (_time.time(), merged)
    return len(merged)


@router.post("/docs/upload")
async def docs_upload(
    files: list[UploadFile] = File(...),
    session_id: str = Form(""),
) -> dict:
    """Parse + chunk + embed uploaded documents under a session id.

    Returns the session id (newly minted if the client did not send one) plus
    a per-file summary. Documents stay in memory; they are not retained on
    disk and only their chunks (which the customer themselves uploaded) ever
    reach the LLM during a later /ask call.
    """
    from api import main  # deferred: see module docstring
    sid = session_id or uuid.uuid4().hex

    # Per-request caps (Finding 4): bound file count and total bytes before we
    # parse anything, so a single request cannot exhaust memory by sending many
    # files each just under the single-file cap.
    if len(files) > main.MAX_DOCS_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=413,
            detail=(f"Too many files in one request "
                    f"(limit {main.MAX_DOCS_FILES_PER_REQUEST}). Upload fewer files "
                    "or split the request."),
        )

    new_chunks: list[docs_mod.Chunk] = []
    file_info: list[dict] = []
    total_bytes = 0
    for f in files:
        data = await main._read_capped(f)
        total_bytes += len(data)
        if total_bytes > main.MAX_DOCS_TOTAL_BYTES:
            raise HTTPException(
                status_code=413,
                detail=(f"Upload too large: total across files exceeds "
                        f"{main.MAX_DOCS_TOTAL_BYTES // (1024 * 1024)} MB. Upload "
                        "fewer or smaller files."),
            )
        try:
            parsed = docs_mod.parse_and_chunk(f.filename or "doc", data)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        doc_id = uuid.uuid4().hex
        for i, (page, text) in enumerate(parsed):
            new_chunks.append(docs_mod.Chunk(
                doc_id=doc_id,
                doc_name=f.filename or "doc",
                chunk_idx=i,
                text=text,
                page=page,
            ))
        file_info.append({"name": f.filename, "chunks": len(parsed)})

    if new_chunks:
        embs = docs_mod.embed_texts([c.text for c in new_chunks])
        for c, e in zip(new_chunks, embs):
            c.embedding = e

    total = _doc_store_append(sid, new_chunks)
    return {
        "session_id": sid,
        "files": file_info,
        "total_chunks": total,
    }


class AskReq(BaseModel):
    question: str
    session_id: str | None = None
    use_web: bool = False
    # Optional client-supplied analysis snapshot (e.g. the JSON for an
    # uploaded-CSV result). Defaults to the demo diagnostic on the sample.
    analysis: dict | None = None


@router.post("/ask")
def ask_endpoint(req: AskReq) -> dict:
    """RAG over analysis + uploaded docs + (optional) web search."""
    chunks = _doc_store_get(req.session_id) if req.session_id else []
    analysis = req.analysis if req.analysis is not None else _diagnostic_payload(
        str(DEMO_CSV), 0.15,
    )
    ans = rag_mod.ask(req.question, analysis, chunks, use_web=req.use_web)
    return {
        "text": ans.text,
        "used_web": ans.used_web,
        "session_id": req.session_id,
        "citations": [
            {
                "kind": c.kind,
                "title": c.title,
                "snippet": c.snippet,
                "detail": c.detail,
            }
            for c in ans.citations
        ],
    }
