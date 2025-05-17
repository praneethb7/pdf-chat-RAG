"""
Corrective RAG (CRAG) — relevance evaluation and query rewriting.

Flow
----
1. BM25 retrieval (embeddings.py)
2. evaluate_relevance()  — fast Groq call; scores "relevant" / "partial" / "irrelevant"
3. If irrelevant → rewrite_query() — Groq rewrites with academic vocab + expands
   abbreviations → re-retrieve
4. Generate answer (llm.py) from the corrected context

Why CRAG fixes the retrieval failures we observed
--------------------------------------------------
BM25 returns chunks that share tokens with the query. When a user asks
"Why is the Transformer better than RNNs?", BM25 returns chunks containing
"Transformer" (architecture tables, Figure 1) rather than the "Why Self-Attention"
section (which uses "recurrent", "sequential", "parallelization"). The evaluator
detects the mismatch; the rewriter expands "RNNs" → "recurrent neural networks"
and replaces "better" → "advantages" so the next BM25 pass finds the right section.
"""

from __future__ import annotations

import logging
import re

from groq import Groq

from config import GROQ_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_EVAL_SYSTEM = """\
You are a retrieval quality evaluator. Given a question and a set of retrieved
document passages, assess whether the passages contain enough information to
answer the question.

Respond with exactly one word:
  relevant   — the passages directly contain the information needed to answer
  partial    — the passages are related but may not fully address the question
  irrelevant — the passages do not help answer the question at all
"""

_REWRITE_SYSTEM = """\
Rewrite the user's question to improve keyword-based document retrieval:
  • Expand abbreviations (RNNs → recurrent neural networks, CNNs →
    convolutional neural networks, LLMs → large language models, etc.)
  • Replace informal comparisons with technical equivalents
    ("better than" → "advantages over", "smarter" → "higher accuracy")
  • Add domain synonyms that might appear in an academic paper
  • Keep the meaning exactly the same
  • Output ONLY the rewritten question — no explanation, no punctuation changes
    beyond what's needed
"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

Relevance = str  # "relevant" | "partial" | "irrelevant"


def evaluate_relevance(
    client: Groq,
    question: str,
    chunk_texts: list[str],
) -> Relevance:
    """
    Ask the LLM whether the retrieved passages actually address the question.
    Uses at most the first 3 chunks to keep the prompt short.
    """
    context = "\n---\n".join(chunk_texts[:3])
    prompt = f"Question: {question}\n\nPassages:\n{context}"

    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": _EVAL_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=10,
            temperature=0.0,
        )
        raw = resp.choices[0].message.content.strip().lower()
    except Exception as exc:
        logger.warning("Relevance evaluation failed (%s) — defaulting to partial", exc)
        return "partial"

    if re.search(r"\birrelevant\b", raw):
        verdict = "irrelevant"
    elif re.search(r"\bpartial\b", raw):
        verdict = "partial"
    else:
        verdict = "relevant"

    logger.info("CRAG relevance verdict: %s (raw=%r)", verdict, raw)
    return verdict


def rewrite_query(client: Groq, question: str) -> str:
    """
    Rewrite the question so BM25 can find the relevant section in the document.
    Falls back to the original question on any error.
    """
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": _REWRITE_SYSTEM},
                {"role": "user", "content": question},
            ],
            max_tokens=80,
            temperature=0.0,
        )
        rewritten = resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("Query rewrite failed (%s) — using original", exc)
        return question

    logger.info("CRAG rewritten query: %r → %r", question, rewritten)
    return rewritten or question
