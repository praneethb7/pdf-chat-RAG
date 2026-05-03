"""
Evaluation test cases for the PDF Chat RAG pipeline.

Each TestCase captures:
- query          : the exact question sent to /api/chat
- should_answer  : True if the PDF contains a grounded answer; False if the
                   system must refuse (isOutOfScope=True)
- expected_behavior : plain-English description of what a correct system does
                      (intentionally NOT an exact expected answer string, so
                      the evaluator checks behaviour, not literal text)
- tags           : optional labels for filtering / reporting

The 5 valid queries all have clear, single-source answers on specific pages of
the ClimateCore Platform Technical Overview PDF.

The 3 invalid queries are provably out-of-scope: none of the relevant facts
appear anywhere in the PDF, so a correct system must refuse.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class TestCase:
    query: str
    should_answer: bool
    expected_behavior: str
    tags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Valid queries — answerable from the PDF
# ---------------------------------------------------------------------------

VALID_CASES: list[TestCase] = [
    TestCase(
        query="Who founded ClimateCore?",
        should_answer=True,
        expected_behavior=(
            "System returns a grounded answer naming 'Dr. Elena Marchetti' as the "
            "founder, backed by a citation from page 1 of the document."
        ),
        tags=["factual", "page-1", "person"],
    ),
    TestCase(
        query="How many climate data sources does DataVault integrate?",
        should_answer=True,
        expected_behavior=(
            "System returns a grounded answer stating '47' data sources, "
            "with a citation from the Core Modules section (page 2)."
        ),
        tags=["factual", "page-2", "number"],
    ),
    TestCase(
        query="What is the median API response time for ClimateCore?",
        should_answer=True,
        expected_behavior=(
            "System returns a grounded answer of '127 milliseconds', "
            "with a citation from the Technical Architecture section (page 3)."
        ),
        tags=["factual", "page-3", "performance", "chunk-removal-target"],
    ),
    TestCase(
        query="How much does the Professional subscription plan cost per month?",
        should_answer=True,
        expected_behavior=(
            "System returns a grounded answer of '$249 per month', "
            "with a citation from the Pricing section (page 4)."
        ),
        tags=["factual", "page-4", "pricing"],
    ),
    TestCase(
        query="What encryption standard is used for data at rest?",
        should_answer=True,
        expected_behavior=(
            "System returns a grounded answer of 'AES-256', "
            "with a citation from the Security and Compliance section (page 5)."
        ),
        tags=["factual", "page-5", "security"],
    ),
]

# ---------------------------------------------------------------------------
# Invalid queries — NOT answerable from the PDF
# ---------------------------------------------------------------------------

INVALID_CASES: list[TestCase] = [
    TestCase(
        query="What is ClimateCore's current stock price?",
        should_answer=False,
        expected_behavior=(
            "System refuses with isOutOfScope=True and returns no citations, "
            "because no stock price or financial market data appears in the PDF."
        ),
        tags=["out-of-scope", "financial"],
    ),
    TestCase(
        query="Who are ClimateCore's main competitors?",
        should_answer=False,
        expected_behavior=(
            "System refuses with isOutOfScope=True and returns no citations, "
            "because competitor information is not mentioned anywhere in the PDF."
        ),
        tags=["out-of-scope", "competitive-analysis"],
    ),
    TestCase(
        query="What is the capital of France?",
        should_answer=False,
        expected_behavior=(
            "System refuses with isOutOfScope=True and returns no citations, "
            "because this general-knowledge question has no relation to the PDF content."
        ),
        tags=["out-of-scope", "general-knowledge"],
    ),
]

# ---------------------------------------------------------------------------
# Combined ordered list (valid first, then invalid)
# ---------------------------------------------------------------------------

ALL_CASES: list[TestCase] = VALID_CASES + INVALID_CASES

# ---------------------------------------------------------------------------
# Chunk-removal simulation config
# ---------------------------------------------------------------------------

# This is the query whose grounded answer disappears when we surgically remove
# the chunk containing the performance metrics from the FAISS index.
CHUNK_REMOVAL_QUERY = "What is the median API response time for ClimateCore?"

# Substring that uniquely identifies the target chunk in chunks.json.
# If this string is absent from a chunk's text, the chunk is kept.
CHUNK_REMOVAL_KEYWORD = "127 milliseconds"
