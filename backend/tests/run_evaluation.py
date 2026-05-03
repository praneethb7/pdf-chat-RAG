"""
Automated evaluation runner for the PDF Chat RAG pipeline.

What this script does
---------------------
1. Starts with a health-check against the running backend (default: localhost:3001).
2. Generates the ClimateCore sample PDF if it does not already exist.
3. Uploads the PDF via POST /api/upload.
4. Runs all 8 test cases (5 valid + 3 invalid) and logs:
      - The answer text
      - Whether a citation was returned
      - Whether the system correctly answered or refused
      - PASS / FAIL verdict for each case
5. Runs the chunk-removal simulation:
      a. Backs up the FAISS chunks.json for the uploaded session.
      b. Removes the chunk(s) containing the performance-metrics text.
      c. Rebuilds the FAISS index from the remaining chunks.
      d. Re-queries "What is the median API response time?"
      e. Compares the degraded result to the original answer and shows the diff.
      f. Restores the original chunks.json and index.

Prerequisites
-------------
- Backend running:  cd backend && uvicorn app.main:app --port 3001
- Install test deps: pip install requests
- .env set with a valid ANTHROPIC_API_KEY

Usage
-----
    # From the backend/ directory:
    python -m tests.run_evaluation

    # Or from the project root:
    python backend/tests/run_evaluation.py --base-url http://localhost:3001
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import requests

# Make backend package importable regardless of cwd
_BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from tests.generate_pdf import create_sample_pdf
from tests.test_cases import ALL_CASES, CHUNK_REMOVAL_KEYWORD, CHUNK_REMOVAL_QUERY, TestCase

# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def green(s: str)  -> str: return f"{GREEN}{s}{RESET}"
def red(s: str)    -> str: return f"{RED}{s}{RESET}"
def yellow(s: str) -> str: return f"{YELLOW}{s}{RESET}"
def cyan(s: str)   -> str: return f"{CYAN}{s}{RESET}"
def bold(s: str)   -> str: return f"{BOLD}{s}{RESET}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_PDF = Path(__file__).parent / "fixtures" / "climatecore_overview.pdf"


def _section(title: str) -> None:
    print(f"\n{bold('=' * 70)}")
    print(f"{bold(f'  {title}')}")
    print(f"{bold('=' * 70)}")


def _health_check(base_url: str) -> None:
    _section("STEP 1 — Health check")
    try:
        r = requests.get(f"{base_url}/api/health", timeout=5)
        r.raise_for_status()
        print(green(f"  Backend is up: {r.json()}"))
    except Exception as exc:
        print(red(f"  Backend not reachable at {base_url}: {exc}"))
        print(red("  Start the backend first: uvicorn app.main:app --port 3001"))
        sys.exit(1)


def _upload_pdf(base_url: str) -> tuple[str, int]:
    _section("STEP 2 — Upload sample PDF")
    if not SAMPLE_PDF.exists():
        print(yellow("  PDF not found — generating …"))
        create_sample_pdf(SAMPLE_PDF)
    else:
        print(f"  Using cached PDF: {SAMPLE_PDF}")

    with open(SAMPLE_PDF, "rb") as f:
        r = requests.post(
            f"{base_url}/api/upload",
            files={"pdf": ("climatecore_overview.pdf", f, "application/pdf")},
            timeout=60,
        )

    if r.status_code != 200:
        print(red(f"  Upload failed ({r.status_code}): {r.text}"))
        sys.exit(1)

    data = r.json()
    session_id: str = data["sessionId"]
    page_count: int = data["pageCount"]
    print(green(f"  Uploaded successfully — sessionId: {session_id}"))
    print(f"  Pages: {page_count}  |  Chunks message: {data['message']}")
    return session_id, page_count


def _ask(base_url: str, session_id: str, question: str) -> dict[str, Any]:
    r = requests.post(
        f"{base_url}/api/chat",
        json={"sessionId": session_id, "question": question},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------

def _run_test_cases(base_url: str, session_id: str) -> list[dict]:
    _section("STEP 3 — Run all test cases")

    results: list[dict] = []

    for i, case in enumerate(ALL_CASES, start=1):
        kind = "VALID  " if case.should_answer else "INVALID"
        print(f"\n  [{i}/{len(ALL_CASES)}] {cyan(kind)}  {case.query}")
        print(f"         Expected: {case.expected_behavior}")

        resp = _ask(base_url, session_id, case.query)

        answer      = resp.get("answer", "")
        citations   = resp.get("citations", [])
        out_of_scope = resp.get("isOutOfScope", True)

        has_citation = len(citations) > 0
        refused      = out_of_scope

        # Determine PASS / FAIL
        if case.should_answer:
            # Must answer AND provide at least one citation
            passed = (not refused) and has_citation
        else:
            # Must refuse
            passed = refused

        tag = green("PASS") if passed else red("FAIL")

        print(f"         Answer    : {answer[:200]}")
        print(f"         Citations : {has_citation} ({len(citations)} returned)")
        print(f"         Refused   : {refused}")
        print(f"         Verdict   : {tag}")

        results.append(
            {
                "index": i,
                "query": case.query,
                "should_answer": case.should_answer,
                "answered": not refused,
                "has_citation": has_citation,
                "passed": passed,
                "answer_preview": answer[:200],
                "citation_count": len(citations),
                "first_citation": citations[0] if citations else None,
            }
        )

    return results


def _print_summary(results: list[dict]) -> None:
    _section("TEST SUMMARY")
    passed = sum(1 for r in results if r["passed"])
    total  = len(results)

    headers = ["#", "Query (truncated)", "Type", "Cited", "Refused", "Verdict"]
    col_w   = [3, 44, 8, 6, 8, 7]

    def row(*cells: str) -> str:
        return "  " + "  ".join(str(c).ljust(w) for c, w in zip(cells, col_w))

    print(row(*headers))
    print("  " + "-" * 82)

    for r in results:
        kind    = "valid" if r["should_answer"] else "invalid"
        verdict = green("PASS") if r["passed"] else red("FAIL")
        print(row(
            str(r["index"]),
            r["query"][:44],
            kind,
            str(r["has_citation"]),
            str(not r["answered"]),
            verdict,
        ))

    print()
    colour = green if passed == total else (yellow if passed >= total // 2 else red)
    print(f"  {bold('Result:')} {colour(f'{passed}/{total} passed')}")


# ---------------------------------------------------------------------------
# Chunk-removal simulation
# ---------------------------------------------------------------------------

def _chunk_removal_simulation(base_url: str, session_id: str) -> None:
    _section("STEP 4 — Chunk-removal simulation")

    print(f"  Target query   : {CHUNK_REMOVAL_QUERY}")
    print(f"  Removed keyword: '{CHUNK_REMOVAL_KEYWORD}'")
    print()

    # Locate the session's storage directory
    storage_dir = _BACKEND_DIR / "storage" / session_id
    chunks_path = storage_dir / "chunks.json"
    index_path  = storage_dir / "index.faiss"

    if not chunks_path.exists():
        print(red(f"  chunks.json not found at {chunks_path} — skipping simulation"))
        return

    # ── Baseline answer (full index) ──────────────────────────────────────
    print("  [A] Querying with FULL index …")
    full_resp    = _ask(base_url, session_id, CHUNK_REMOVAL_QUERY)
    full_answer  = full_resp.get("answer", "")
    full_refused = full_resp.get("isOutOfScope", True)
    full_cited   = len(full_resp.get("citations", [])) > 0

    print(f"      Answer  : {full_answer[:300]}")
    print(f"      Cited   : {full_cited}")
    print(f"      Refused : {full_refused}")

    # ── Back up original files ─────────────────────────────────────────────
    backup_chunks = storage_dir / "chunks.json.bak"
    backup_index  = storage_dir / "index.faiss.bak"
    shutil.copy2(chunks_path, backup_chunks)
    shutil.copy2(index_path,  backup_index)

    try:
        # ── Load chunks, remove target chunk(s) ───────────────────────────
        with open(chunks_path, encoding="utf-8") as f:
            all_chunks: list[dict] = json.load(f)

        original_count = len(all_chunks)
        kept_chunks    = [c for c in all_chunks if CHUNK_REMOVAL_KEYWORD not in c["text"]]
        removed_count  = original_count - len(kept_chunks)

        if removed_count == 0:
            print(yellow(
                f"\n  WARNING: No chunks contained '{CHUNK_REMOVAL_KEYWORD}'. "
                "Simulation skipped."
            ))
            return

        print(f"\n  Removed {removed_count} chunk(s) out of {original_count} total.")

        # ── Rebuild FAISS index from remaining chunks ──────────────────────
        print("  Rebuilding FAISS index without the removed chunk(s) …")
        _rebuild_index(session_id, kept_chunks, chunks_path, index_path)

        # Give the app 0.5 s to notice the file changed (it reads from disk on
        # cache-miss; we force a cache miss by POSTing a fresh question below)
        time.sleep(0.5)

        # Force the backend to reload from the mutated disk files by deleting
        # the session from its in-memory cache via the DELETE endpoint, then
        # re-querying (it will reload from disk automatically).
        try:
            requests.delete(f"{base_url}/api/chat/session/{session_id}", timeout=5)
        except Exception:
            pass  # If this fails the reload still happens on the next request

        # Re-upload so the session exists again (delete wiped it)
        print("  Re-uploading PDF so session is fresh for degraded query …")
        with open(SAMPLE_PDF, "rb") as f:
            r = requests.post(
                f"{base_url}/api/upload",
                files={"pdf": ("climatecore_overview.pdf", f, "application/pdf")},
                timeout=60,
            )
        new_session_id = r.json()["sessionId"]

        # Overwrite the new session's index with the mutated one
        new_storage = _BACKEND_DIR / "storage" / new_session_id
        shutil.copy2(chunks_path, new_storage / "chunks.json")
        _rebuild_index(new_session_id, kept_chunks,
                       new_storage / "chunks.json",
                       new_storage / "index.faiss")

        # ── Degraded answer (partial index) ───────────────────────────────
        print("\n  [B] Querying with DEGRADED index (chunk removed) …")
        deg_resp    = _ask(base_url, new_session_id, CHUNK_REMOVAL_QUERY)
        deg_answer  = deg_resp.get("answer", "")
        deg_refused = deg_resp.get("isOutOfScope", True)
        deg_cited   = len(deg_resp.get("citations", [])) > 0

        print(f"      Answer  : {deg_answer[:300]}")
        print(f"      Cited   : {deg_cited}")
        print(f"      Refused : {deg_refused}")

        # ── Side-by-side diff ─────────────────────────────────────────────
        _section("Chunk-removal Result Comparison")
        print(f"  Query: {CHUNK_REMOVAL_QUERY}\n")

        print(f"  {'Before removal':40}  {'After removal':40}")
        print(f"  {'-'*40}  {'-'*40}")
        print(f"  {'Answer:':40}  {'Answer:':40}")
        for line in _wrap(full_answer, 40):
            print(f"  {green(line):50}  ", end="")
        print()
        for line in _wrap(deg_answer, 40):
            print(f"  {'':42}  {red(line):50}")
        print()
        print(f"  Cited   : {green(str(full_cited)):20}  Cited   : {red(str(deg_cited))}")
        print(f"  Refused : {green(str(full_refused)):20}  Refused : {red(str(deg_refused))}")

        if deg_refused and not full_refused:
            print(f"\n  {bold(green('✓ Simulation passed:'))} removing the source chunk "
                  "caused the system to correctly refuse the question.")
        elif not deg_refused and not full_refused:
            print(f"\n  {yellow('⚠ System still answered after chunk removal.')} "
                  "This may indicate another chunk partially covers the answer.")
        else:
            print(f"\n  {yellow('⚠ Unexpected outcome — inspect logs for details.')}")

        # Clean up the degraded session
        try:
            requests.delete(f"{base_url}/api/chat/session/{new_session_id}", timeout=5)
        except Exception:
            pass

    finally:
        # ── Always restore originals ───────────────────────────────────────
        if backup_chunks.exists():
            shutil.copy2(backup_chunks, chunks_path)
            backup_chunks.unlink()
        if backup_index.exists():
            shutil.copy2(backup_index, index_path)
            backup_index.unlink()


def _rebuild_index(session_id: str, chunks: list[dict],
                   chunks_path: Path, index_path: Path) -> None:
    """Encode *chunks* and write a fresh FAISS index to *index_path*."""
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=64,
        show_progress_bar=False,
        convert_to_numpy=True,
    ).astype(np.float32)

    dim   = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    faiss.write_index(index, str(index_path))
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)


def _wrap(text: str, width: int) -> list[str]:
    """Very simple word-wrap."""
    words, lines, line = text.split(), [], []
    for w in words:
        if sum(len(x) + 1 for x in line) + len(w) > width:
            lines.append(" ".join(line))
            line = [w]
        else:
            line.append(w)
    if line:
        lines.append(" ".join(line))
    return lines or [""]


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PDF Chat evaluation suite")
    parser.add_argument(
        "--base-url",
        default=os.getenv("BACKEND_URL", "http://localhost:3001"),
        help="Base URL of the running backend (default: http://localhost:3001)",
    )
    parser.add_argument(
        "--skip-chunk-removal",
        action="store_true",
        help="Skip the chunk-removal simulation (faster, no FAISS rebuild)",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    _health_check(base_url)
    session_id, _ = _upload_pdf(base_url)
    results        = _run_test_cases(base_url, session_id)
    _print_summary(results)

    if not args.skip_chunk_removal:
        _chunk_removal_simulation(base_url, session_id)

    # Final cleanup
    try:
        requests.delete(f"{base_url}/api/chat/session/{session_id}", timeout=5)
    except Exception:
        pass

    total  = len(results)
    passed = sum(1 for r in results if r["passed"])
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
