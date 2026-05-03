"""
FastAPI application — PDF Chat backend.

Endpoints (API-compatible with the existing TypeScript frontend)
---------------------------------------------------------------
POST   /api/upload                   Upload a PDF; extract, chunk, embed, persist
POST   /api/chat                     Ask a question about an uploaded PDF
GET    /api/chat/session/{sessionId} Get session metadata
DELETE /api/chat/session/{sessionId} Delete a session
GET    /api/health                   Liveness check
"""

from __future__ import annotations

import json
import logging
import logging.config
import os
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
# Allow imports from the backend root (where config.py lives)
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    CORS_ORIGIN,
    LLM_MODEL,
    MAX_PDF_SIZE_MB,
    PORT,
    STORAGE_DIR,
    UPLOAD_DIR,
)
from app.pdf_processor import extract_pages
from app.chunker import chunk_pages
from app.embeddings import FAISSStore
from app.llm import answer_question

# ---------------------------------------------------------------------------
# Startup / teardown
# ---------------------------------------------------------------------------


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    os.makedirs(STORAGE_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    yield


app = FastAPI(title="PDF Chat API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory session cache (avoids reloading FAISS index on every request)
# ---------------------------------------------------------------------------

_session_cache: dict[str, FAISSStore] = {}
_session_info: dict[str, dict] = {}

_INFO_FILE = "info.json"


def _info_path(session_id: str) -> str:
    return os.path.join(STORAGE_DIR, session_id, _INFO_FILE)


def _load_info(session_id: str) -> dict | None:
    path = _info_path(session_id)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_info(session_id: str, info: dict) -> None:
    os.makedirs(os.path.join(STORAGE_DIR, session_id), exist_ok=True)
    with open(_info_path(session_id), "w", encoding="utf-8") as f:
        json.dump(info, f)


def _get_store(session_id: str) -> FAISSStore:
    """Return the FAISSStore for a session, loading from disk if needed."""
    if session_id not in _session_cache:
        if not FAISSStore.exists(session_id):
            raise HTTPException(
                status_code=404,
                detail="Session not found. Please re-upload your PDF.",
            )
        _session_cache[session_id] = FAISSStore.load(session_id)
    return _session_cache[session_id]


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    sessionId: str
    question: str


class Citation(BaseModel):
    page: int
    snippet: str


class UploadResponse(BaseModel):
    sessionId: str
    fileName: str
    pageCount: int
    message: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    isOutOfScope: bool


class SessionInfo(BaseModel):
    fileName: str
    pageCount: int
    createdAt: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/api/upload", response_model=UploadResponse)
async def upload_pdf(pdf: UploadFile = File(...)):
    """
    Accept a PDF, extract text page-by-page, chunk into token windows,
    generate sentence-transformer embeddings, and persist a FAISS index.
    """
    if pdf.content_type not in ("application/pdf", "application/octet-stream"):
        if not (pdf.filename or "").lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400, detail="Only PDF files are accepted."
            )

    max_bytes = MAX_PDF_SIZE_MB * 1024 * 1024
    content = await pdf.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {MAX_PDF_SIZE_MB} MB limit.",
        )

    session_id = str(uuid.uuid4())
    original_name = pdf.filename or "document.pdf"
    pdf_path = os.path.join(UPLOAD_DIR, f"{session_id}.pdf")

    try:
        # Persist the uploaded file
        with open(pdf_path, "wb") as fh:
            fh.write(content)

        # ── 1. Extract text with page numbers ────────────────────────────────
        pages = extract_pages(pdf_path)

        # ── 2. Chunk into 500–800 token windows (with 150-token overlap) ─────
        chunks = chunk_pages(pages)
        if not chunks:
            raise HTTPException(
                status_code=422, detail="Could not extract any text from the PDF."
            )

        # ── 3. Embed + build FAISS index ──────────────────────────────────────
        store = FAISSStore(session_id)
        store.build(chunks)
        store.save()

        # ── 4. Persist session metadata ───────────────────────────────────────
        info = {
            "fileName": original_name,
            "pageCount": len(pages),
            "createdAt": datetime.utcnow().isoformat(),
        }
        _save_info(session_id, info)

        _session_cache[session_id] = store
        _session_info[session_id] = info

        return UploadResponse(
            sessionId=session_id,
            fileName=original_name,
            pageCount=len(pages),
            message=(
                f"Processed {len(pages)} pages into {len(chunks)} chunks successfully."
            ),
        )

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to process PDF: {exc}"
        ) from exc
    finally:
        # Remove the raw PDF file; the FAISS index is the persistent artefact
        if os.path.isfile(pdf_path):
            os.remove(pdf_path)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    """
    Answer a user question using only the content of the uploaded PDF.

    Strict grounding is enforced at two layers:
    1. Similarity threshold — if the top retrieved chunk scores below the
       configured threshold, the LLM is never called.
    2. System prompt — Claude is instructed to output "grounded: false" if
       the context does not contain the answer.
    """
    session_id = body.sessionId.strip()
    question = body.question.strip()

    if not session_id:
        raise HTTPException(status_code=400, detail="sessionId is required.")
    if not question:
        raise HTTPException(status_code=400, detail="question must be non-empty.")
    if len(question) > 2000:
        raise HTTPException(
            status_code=400, detail="Question exceeds 2000 character limit."
        )

    store = _get_store(session_id)

    try:
        result = answer_question(store, question)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Error generating answer: {exc}"
        ) from exc

    return ChatResponse(
        answer=result["answer"],
        citations=[Citation(**c) for c in result["citations"]],
        isOutOfScope=result["isOutOfScope"],
    )


@app.get("/api/chat/session/{session_id}", response_model=SessionInfo)
def get_session(session_id: str):
    """Return metadata for a session (file name, page count, creation time)."""
    info = _session_info.get(session_id) or _load_info(session_id)
    if not info:
        raise HTTPException(status_code=404, detail="Session not found.")
    _session_info[session_id] = info
    return SessionInfo(**info)


@app.delete("/api/chat/session/{session_id}")
def delete_session(session_id: str):
    """Remove the FAISS index and all metadata for a session."""
    exists = FAISSStore.exists(session_id) or session_id in _session_info

    if not exists:
        # Check disk one more time before 404-ing
        if not _load_info(session_id):
            raise HTTPException(status_code=404, detail="Session not found.")

    _session_cache.pop(session_id, None)
    _session_info.pop(session_id, None)

    store = FAISSStore(session_id)
    store.delete()

    return {"message": "Session deleted."}


@app.get("/api/health")
def health():
    return {"status": "ok", "model": LLM_MODEL, "retrieval": "BM25"}


# ---------------------------------------------------------------------------
# Entry-point when run directly: python -m app.main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)
