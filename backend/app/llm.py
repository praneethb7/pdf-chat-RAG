"""
Groq LLM integration with strict grounding.

Grounding layers
----------------
Layer 1 (retrieval gate)  — If the highest cosine similarity among retrieved
    chunks is below SIMILARITY_THRESHOLD the LLM is never called and a
    standardised refusal is returned immediately.  Meta-queries (summarise,
    explain section, etc.) bypass this gate since they embed poorly against
    specific chunks but are clearly document-scoped.

Layer 2 (prompt)          — The system prompt explicitly forbids external
    knowledge, mandates verbatim citations, and instructs the model to set
    grounded=false rather than speculate.

Layer 3 (citation validation + retry) — After parsing the LLM response, if
    grounded=true but no valid citations were returned, the call is retried up
    to MAX_CITATION_RETRIES times with an escalating reminder.  If citations
    are still absent after all retries, a refusal is returned rather than
    silently accepting an uncited answer.

Temperature is 0 for fully deterministic output.
"""

from __future__ import annotations

import json
import logging
import re

from groq import Groq

from config import (
    GROQ_API_KEY,
    LLM_MODEL,
    LLM_TEMPERATURE,
    MAX_CITATION_RETRIES,
    SIMILARITY_THRESHOLD,
    TOP_K,
)
from app.embeddings import FAISSStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

Citation = dict  # {"page": int, "snippet": str}
QueryResult = dict  # {"answer": str, "citations": list[Citation], "isOutOfScope": bool}

# Patterns that indicate the user is asking about the document as a whole.
# These queries embed poorly against specific chunks, so we skip the threshold gate.
_META_QUERY_PATTERNS = re.compile(
    r"\b(summar\w+|overview|outline|section\s+\w|chapter\s+\w|explain\s+section"
    r"|what\s+is\s+this\s+(document|pdf|about)"
    r"|list\s+all|enumerate|key\s+points?|main\s+points?|highlights?)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a strict PDF document assistant. Your ONLY purpose is to answer \
questions using the context passages supplied in the user message.

══════════════════════ NON-NEGOTIABLE RULES ══════════════════════
1. USE ONLY THE PROVIDED CONTEXT FOR ANSWERS.
   • Do NOT draw on any training knowledge, world knowledge, or facts
     outside the context passages — not even to fill small gaps.
   • If the context does not contain enough information, set "grounded"
     to false and leave "answer" as null. Never guess or infer.
   • You MAY use domain knowledge to interpret the question (e.g., recognise
     that "RNNs" means "recurrent neural networks", "LLMs" means "large
     language models", etc.) so you can find the relevant passages. But your
     answer must still be drawn exclusively from the context.

2. WRITE A COMPLETE, EXPLANATORY ANSWER.
   • Your answer must fully explain or summarise the relevant information
     found in the context. Do NOT simply repeat a section heading or title.
   • If asked "what is X?", explain what X is using the context text.
   • If asked "why" or "how", explain the reasoning found in the context.
   • Aim for 2–5 sentences unless the question calls for a list or summary.

3. EVERY GROUNDED ANSWER REQUIRES CITATIONS.
   • You MUST include at least one citation with a verbatim snippet from
     the context whenever grounded=true.
   • If you cannot find a passage that directly supports your answer,
     the answer is NOT grounded — set grounded=false.
   • Snippets must be copied word-for-word from the context; do not
     paraphrase or synthesise.

4. NO SPECULATION, EVER.
   • "Probably", "likely", "I think", "it seems", etc. are forbidden.
   • If you are uncertain, set grounded=false.

5. OUTPUT FORMAT — valid JSON only, no markdown fences, no extra keys:
{
  "grounded": true | false,
  "answer": "<complete explanatory answer using only the context>",
  "citations": [
    {"page": <integer>, "snippet": "<exact verbatim quote from context>"}
  ]
}
   • When grounded=false: answer must be null and citations must be [].
══════════════════════════════════════════════════════════════════
"""

_RETRY_REMINDER = """\

IMPORTANT REMINDER: Your previous response was grounded=true but contained \
no citations. This violates the rules. You MUST include at least one citation \
with a verbatim snippet. If you cannot find a supporting passage, set \
grounded=false instead.\
"""

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def answer_question(store: FAISSStore, question: str) -> QueryResult:
    """
    Retrieve relevant chunks, apply all grounding checks, then call Groq.

    Returns a QueryResult compatible with the frontend ChatResponse type.
    """
    # ── Layer 1: similarity-threshold gate ──────────────────────────────────
    hits = store.search(question, top_k=TOP_K)

    if not hits:
        logger.warning("FAISS store returned no hits — refusing")
        return _refusal()

    _log_retrieval(question, hits)

    is_meta = bool(_META_QUERY_PATTERNS.search(question))
    top_score = hits[0][1]
    logger.info("Top similarity score: %.4f (threshold: %.4f, meta: %s)", top_score, SIMILARITY_THRESHOLD, is_meta)
    if not is_meta and top_score < SIMILARITY_THRESHOLD:
        logger.info(
            "Top score %.4f < threshold %.4f — refusing without LLM call",
            top_score,
            SIMILARITY_THRESHOLD,
        )
        return _refusal()
    if is_meta:
        logger.info("Meta-query detected — skipping similarity gate (score=%.4f)", top_score)

    # ── Build context ────────────────────────────────────────────────────────
    context = _build_context(hits)

    # ── Layer 2 + 3: LLM call with citation-validation retry loop ───────────
    client = Groq(api_key=GROQ_API_KEY)
    extra_reminder = ""

    for attempt in range(1, MAX_CITATION_RETRIES + 2):
        logger.info("LLM call attempt %d/%d", attempt, MAX_CITATION_RETRIES + 1)

        raw = _call_llm(client, context, question, extra_reminder)
        result = _parse_response(raw)

        if result["isOutOfScope"]:
            logger.info("Model returned grounded=false — returning refusal")
            return _refusal()

        if result["citations"]:
            logger.info(
                "Answer accepted on attempt %d with %d citation(s)",
                attempt,
                len(result["citations"]),
            )
            return result

        logger.warning(
            "Attempt %d: grounded=true but no valid citations — %s",
            attempt,
            "retrying" if attempt <= MAX_CITATION_RETRIES else "giving up",
        )
        extra_reminder = _RETRY_REMINDER

    logger.error(
        "All %d LLM attempts produced grounded=true but no citations — refusing",
        MAX_CITATION_RETRIES + 1,
    )
    return _refusal()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _refusal() -> QueryResult:
    return {
        "answer": "I cannot answer this question from the provided PDF.",
        "citations": [],
        "isOutOfScope": True,
    }


def _log_retrieval(question: str, hits: list[tuple[dict, float]]) -> None:
    logger.info("Question: %r", question)
    logger.info("Retrieved %d chunk(s):", len(hits))
    for rank, (chunk, score) in enumerate(hits, start=1):
        logger.info(
            "  [%d] page=%d  score=%.4f  text=%r…",
            rank,
            chunk["page_num"],
            score,
            chunk["text"][:100],
        )
    logger.info("Top similarity score: %.4f (threshold: %.4f)", hits[0][1], SIMILARITY_THRESHOLD)


def _build_context(hits: list[tuple[dict, float]]) -> str:
    lines: list[str] = []
    for chunk, score in hits:
        lines.append(f"[Page {chunk['page_num']} | similarity={score:.3f}]\n{chunk['text']}")
    return "\n\n---\n\n".join(lines)


def _call_llm(
    client: Groq,
    context: str,
    question: str,
    extra_reminder: str,
) -> str:
    user_message = (
        f"Context:\n{context}\n\n"
        f"Question: {question}"
        f"{extra_reminder}"
    )
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=LLM_TEMPERATURE,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def _parse_response(raw: str) -> QueryResult:
    """
    Parse Groq's JSON output.

    Returns a QueryResult.  Citations list will be empty if the model returned
    grounded=true but no usable citations — the caller handles retries.
    """
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("JSON parse failure on LLM output: %r", raw[:200])
        return {
            "answer": "I cannot answer this question from the provided PDF.",
            "citations": [],
            "isOutOfScope": True,
        }

    grounded: bool = bool(data.get("grounded", False))

    if not grounded:
        return {
            "answer": "I cannot answer this question from the provided PDF.",
            "citations": [],
            "isOutOfScope": True,
        }

    citations = _normalise_citations(data.get("citations", []))

    return {
        "answer": str(data.get("answer") or "").strip(),
        "citations": citations,
        "isOutOfScope": False,
    }


def _normalise_citations(raw: list[dict]) -> list[Citation]:
    """Validate, deduplicate, and sort citations. Returns [] on total failure."""
    seen: set[int] = set()
    result: list[Citation] = []

    for c in raw:
        try:
            page = int(c["page"])
            snippet = str(c.get("snippet", "")).strip()
        except (KeyError, TypeError, ValueError):
            continue
        if page not in seen and snippet:
            seen.add(page)
            result.append({"page": page, "snippet": snippet})

    return sorted(result, key=lambda c: c["page"])
