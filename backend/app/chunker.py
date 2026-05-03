"""
Split extracted PDF pages into token-bounded chunks.

Strategy
--------
- Encoding: cl100k_base (same tokeniser family as Claude / GPT-4).
- Each page is tokenised independently so chunk page_num metadata is exact.
- Long pages are split with a sliding window of CHUNK_MAX_TOKENS tokens and
  CHUNK_OVERLAP_TOKENS overlap so context is not lost at boundaries.
- Short pages that fall below CHUNK_MIN_TOKENS are still kept as single chunks.

Output
------
List of dicts:
    {
        "page_num":    int,   # 1-based page number from the PDF
        "text":        str,   # decoded chunk text
        "token_count": int,   # number of tokens in this chunk
    }
"""

from __future__ import annotations

import tiktoken

from config import CHUNK_MAX_TOKENS, CHUNK_OVERLAP_TOKENS, CHUNK_MIN_TOKENS

# cl100k_base is available offline; it covers the BPE vocabulary Claude uses
_enc = tiktoken.get_encoding("cl100k_base")


def chunk_pages(pages: list[dict]) -> list[dict]:
    """
    Convert a list of per-page text dicts into token-bounded chunks.

    Args:
        pages: Output of pdf_processor.extract_pages().

    Returns:
        List of chunk dicts with page_num, text, and token_count.
    """
    chunks: list[dict] = []

    for page in pages:
        page_chunks = _chunk_text(page["text"], page["page_num"])
        chunks.extend(page_chunks)

    return chunks


def _chunk_text(text: str, page_num: int) -> list[dict]:
    tokens = _enc.encode(text)

    if not tokens:
        return []

    # Entire page fits in one chunk
    if len(tokens) <= CHUNK_MAX_TOKENS:
        return [{"page_num": page_num, "text": text, "token_count": len(tokens)}]

    # Sliding-window split
    stride = CHUNK_MAX_TOKENS - CHUNK_OVERLAP_TOKENS
    result: list[dict] = []

    for start in range(0, len(tokens), stride):
        window = tokens[start : start + CHUNK_MAX_TOKENS]
        if len(window) < CHUNK_MIN_TOKENS:
            # Tail is too small; merge into previous chunk if one exists
            if result:
                prev = result[-1]
                merged_tokens = _enc.encode(prev["text"]) + window
                prev["text"] = _enc.decode(merged_tokens)
                prev["token_count"] = len(merged_tokens)
            break

        result.append(
            {
                "page_num": page_num,
                "text": _enc.decode(window),
                "token_count": len(window),
            }
        )

    return result
