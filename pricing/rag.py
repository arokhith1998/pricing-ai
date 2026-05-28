"""Ask-your-Pricekeel RAG pipeline.

Retrieves from three sources and synthesizes with a cloud LLM (Claude / GPT):

  1. The structured analysis JSON (always — anchored to the dashboard the
     user is looking at).
  2. The customer's uploaded document chunks (PDF/DOCX/MD/TXT) — top-k by
     cosine similarity on the question's embedding.
  3. The public web — only when explicitly enabled by the user (Tavily).

Every claim the model makes must cite — [A] (analysis), [D#] (doc chunks),
or [W#] (web). The system prompt insists on it. Row-level customer data is
never sent: only the aggregate analysis JSON and the retrieved doc chunks
(which the customer themselves uploaded).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

import numpy as np

from pricing import assist
from pricing.docs import Chunk, embed_query


@dataclass
class Citation:
    kind: str  # "doc" | "analysis" | "web"
    title: str
    snippet: str
    detail: str = ""  # page #, similarity score, url


@dataclass
class Answer:
    text: str
    citations: list[Citation]
    used_web: bool = False


def retrieve_doc_chunks(chunks: list[Chunk], query: str,
                        top_k: int = 4) -> list[tuple[Chunk, float]]:
    """Top-k chunks by cosine similarity against the query embedding."""
    if not chunks:
        return []
    q = embed_query(query)
    scored: list[tuple[Chunk, float]] = []
    for c in chunks:
        if c.embedding is None:
            continue
        scored.append((c, float(np.dot(c.embedding, q))))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def web_search(query: str, max_results: int = 4) -> list[dict]:
    """Web search via Perplexity (preferred) or Tavily (fallback).

    Preference order:
      1. PERPLEXITY_API_KEY -> Perplexity Sonar online (LLM-grounded answer +
         citations baked in; one rich result the model can quote).
      2. TAVILY_API_KEY    -> Tavily search results (n separate snippets).
      3. Neither key       -> [] (caller treats web as unavailable).

    The result list shape stays the same across providers:
      [{"title": str, "content": str, "url": str}, ...]
    """
    if os.environ.get("PERPLEXITY_API_KEY"):
        return _web_perplexity(query, max_results)
    if os.environ.get("TAVILY_API_KEY"):
        return _web_tavily(query, max_results)
    return []


def _web_perplexity(query: str, max_results: int = 4) -> list[dict]:
    """Perplexity Sonar (LLM-grounded answer + URL citations)."""
    try:
        import requests  # urllib3 is already pulled in by requests deps
        model = os.environ.get(
            "PERPLEXITY_MODEL", "llama-3.1-sonar-small-128k-online",
        )
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {os.environ['PERPLEXITY_API_KEY']}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are doing background research for a B2B SaaS "
                            "pricing-intelligence app. Reply with concise, "
                            "factual paragraphs grounded in your search."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                "max_tokens": 700,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        urls = data.get("citations") or []
        # First result = the full Perplexity answer; subsequent = its source URLs.
        results = [{
            "title": "Perplexity research",
            "content": answer,
            "url": urls[0] if urls else "",
        }]
        for u in urls[: max(0, max_results - 1)]:
            results.append({"title": u, "content": "", "url": u})
        return results
    except Exception:  # noqa: BLE001
        return []


def _web_tavily(query: str, max_results: int = 4) -> list[dict]:
    """Tavily search (n separate snippets) — used when Perplexity is not set."""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        res = client.search(
            query=query,
            max_results=max_results,
            include_answer=False,
            search_depth="basic",
        )
        return [
            {
                "title": r.get("title", ""),
                "content": r.get("content", ""),
                "url": r.get("url", ""),
            }
            for r in (res.get("results") or [])
        ]
    except Exception:  # noqa: BLE001
        return []


_SYSTEM = (
    "You are 'Pricekeel' — the in-product assistant for Pricekeel, a B2B SaaS "
    "pricing-intelligence app. Reply as the product's voice (calm, direct, "
    "finance-credible). Answer the user's question using ONLY "
    "the supplied context: the structured analysis JSON (marked [A]), the "
    "retrieved document chunks (marked [D#]) from the customer's uploaded "
    "policy / playbook / contracts, and any retrieved web results (marked "
    "[W#]). EVERY substantive claim MUST be followed by one of these citation "
    "markers. If the context is insufficient to answer confidently, say so "
    "plainly and suggest what the user could upload or ask. Do not speculate "
    "beyond what the citations support. Keep answers under ~200 words unless "
    "the user explicitly asks to elaborate. Tone: direct, no hype, no emoji."
)


def ask(question: str, analysis: dict, chunks: list[Chunk],
        use_web: bool = False, max_doc_chunks: int = 4,
        max_web: int = 4) -> Answer:
    """Run the RAG pipeline and return an Answer with structured citations."""
    doc_hits = retrieve_doc_chunks(chunks, question, top_k=max_doc_chunks)
    web_hits = web_search(question, max_results=max_web) if use_web else []

    parts: list[str] = []
    citations: list[Citation] = []

    # Analysis is always included as [A].
    parts.append(
        "[A] Analysis (deterministic, aggregate JSON — do not infer row-level "
        f"data from this):\n{json.dumps(analysis, default=str)[:6000]}"
    )
    citations.append(Citation(
        kind="analysis",
        title="Diagnostic results",
        snippet="Structured analysis (booked, realization, leakage, signals).",
    ))

    for i, (c, score) in enumerate(doc_hits, start=1):
        marker = f"[D{i}]"
        parts.append(f"{marker} From '{c.doc_name}' (page {c.page or '-'}):\n{c.text}")
        citations.append(Citation(
            kind="doc",
            title=c.doc_name,
            snippet=c.text[:200],
            detail=f"page {c.page or '-'} • cosine {score:.2f}",
        ))

    for i, w in enumerate(web_hits, start=1):
        marker = f"[W{i}]"
        body = (w["content"] or "")[:600]
        parts.append(f"{marker} Web: {w['title']}\n{body}")
        citations.append(Citation(
            kind="web",
            title=w["title"] or w["url"],
            snippet=body[:200],
            detail=w["url"],
        ))

    context = "\n\n".join(parts)
    user_msg = f"QUESTION: {question}\n\nCONTEXT:\n{context}"

    if not assist.has_llm():
        return Answer(
            text="The LLM provider is not configured on this server.",
            citations=citations,
            used_web=bool(web_hits),
        )

    text = assist._complete(_SYSTEM, user_msg, max_tokens=700).strip()
    return Answer(text=text, citations=citations, used_web=bool(web_hits))
