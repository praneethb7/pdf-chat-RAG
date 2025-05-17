# Technical Note — PDF Chat

## 1. Architecture Overview

PDF Chat is a full-stack Corrective RAG (CRAG) application. At upload time the PDF is chunked and indexed with BM25; at query time the most relevant passages are retrieved, evaluated for relevance, optionally corrected via query rewriting, and then passed to the LLM which is constrained to answer only from those passages.

```
┌──────────────────────────────────────────────────────────────────┐
│                       FRONTEND (React + Vite)                     │
│  PDFUpload ──► App State ──► ChatWindow ──► CitationBlock         │
│      │                            │                               │
│      │ POST /api/upload            │ POST /api/chat               │
└──────┼────────────────────────────┼───────────────────────────────┘
       │                            │
┌──────▼────────────────────────────▼───────────────────────────────┐
│                      BACKEND (Python · FastAPI)                    │
│                                                                    │
│  Upload Route                    Chat Route                        │
│  ┌──────────────┐               ┌───────────────────────────────┐ │
│  │  PyMuPDF     │               │  answer_question() — CRAG     │ │
│  │  text extract│               │                               │ │
│  │      ▼       │               │  1. BM25 search (top-5)       │ │
│  │  Token-window│               │  2. Relevance eval (Groq)     │ │
│  │  chunker     │               │  3. Query rewrite if needed   │ │
│  │  (800/150)   │               │  4. Re-retrieve if rewritten  │ │
│  │      ▼       │               │  5. Build context string      │ │
│  │  BM25Store   │               │  6. Groq LLM call             │ │
│  │  (rank-bm25) │               │  7. Parse JSON + citations    │ │
│  └──────────────┘               │  8. Citation-retry loop       │ │
│         │                       └───────────────────────────────┘ │
│  In-memory dict {sessionId: BM25Store}  +  disk persistence       │
└────────────────────────────────────────────────────────────────────┘
```

### Upload pipeline

1. **Text extraction** — PyMuPDF extracts raw text page-by-page, preserving page boundaries for citation attribution.
2. **Chunking** — a custom token-window splitter (tiktoken) creates overlapping 800-token chunks (150-token overlap). Each chunk carries `{ page_num, text }` metadata.
3. **BM25 indexing** — `BM25Okapi` (rank-bm25) indexes the tokenised chunks. The index is rebuilt from `chunks.json` on load — no separate serialisation needed.

### Query pipeline (CRAG)

1. **BM25 retrieve** — top-5 chunks by BM25 score are returned. If no chunks score above 0 (no shared tokens), the query is refused immediately.
2. **Relevance evaluation (CRAG Layer 1)** — a fast Groq LLM call assesses whether the retrieved chunks actually address the question, returning `"relevant"`, `"partial"`, or `"irrelevant"`. Meta-queries (summarise, overview, etc.) skip this step.
3. **Query rewrite (CRAG correction)** — if the evaluator returns `"irrelevant"`, Groq rewrites the query: expanding abbreviations (RNNs → recurrent neural networks), replacing informal language with academic vocabulary (better → advantages over), and adding domain synonyms. The rewritten query re-runs BM25.
4. **Context assembly** — surviving chunks are concatenated with page labels.
5. **LLM answer generation (Layer 2)** — Groq `llama-3.1-8b-instant` receives a strict system prompt and the context. It must respond in JSON with `grounded`, `answer`, and `citations`.
6. **Citation validation + retry (Layer 3)** — if the model returns `grounded=true` but no citations, the call is retried up to `MAX_CITATION_RETRIES` times. After all retries, a refusal is returned.

---

## 2. Design Decisions

### Why CRAG

Standard RAG fails when the question and the answer use different vocabulary. Example: "Why is the Transformer better than RNNs?" embeds or matches chunks containing the word "Transformer" prominently (architecture diagrams, results tables) rather than the "Why Self-Attention" section (which uses "recurrent layers", "sequential operations", "parallelization"). The LLM then correctly returns `grounded=false` because it received the wrong context.

CRAG fixes this by detecting the mismatch before the answer LLM call and correcting the retrieval. The correction uses only Groq — no additional API key or service.

### BM25 over dense embeddings

The original design used `all-MiniLM-L6-v2` (sentence-transformers) for semantic embeddings, then switched to fastembed (ONNX) to reduce memory. Both failed on Render's 512 MB free tier — ONNX runtime alone requires ~150 MB, plus model weights, plus the rest of the application stack.

BM25 uses ~5 MB of RAM regardless of document size. For technical PDFs with precise domain terminology, BM25 retrieval quality is competitive with generic sentence-embedding models: exact term matching is often better than semantic approximation for specific factual queries. CRAG's query rewriter compensates for the vocabulary-mismatch weakness inherent to keyword search.

### Groq free tier for all LLM calls

`llama-3.1-8b-instant` handles three roles: relevance evaluation (1 call, max 10 tokens), query rewriting (1 call, max 80 tokens), and answer generation (1–3 calls). Worst case is 5 Groq calls per user question. At 14,400 requests/day the effective capacity is ~2,800 CRAG-corrected answers/day.

### BM25Store with disk persistence

Sessions survive backend restarts. `chunks.json` is written on upload and read on first request. `BM25Okapi` is rebuilt from the chunk text on load — this takes milliseconds and requires no additional serialisation format.

### Token-window chunker parameters

**Chunk size: 800 tokens / Overlap: 150 tokens**

- 800 tokens covers one coherent idea while keeping BM25 term frequency signals focused.
- 150-token overlap prevents facts at chunk boundaries from being lost.
- Chunks below `CHUNK_MIN_TOKENS` (50) are discarded to avoid near-empty noise.

### Temperature 0

Fully deterministic output for all three LLM roles (evaluation, rewrite, answer generation).

---

## 3. Trade-offs

| Decision | Benefit | Cost |
|---|---|---|
| BM25 retrieval | Fits in 512 MB, no model download, fast | Vocabulary-sensitive; misses paraphrased queries |
| CRAG correction | Fixes vocabulary mismatch at query time | +1–2 Groq API calls per corrected query |
| Groq for all LLM roles | Single API key, free tier | 14,400 req/day shared across eval + rewrite + answer |
| In-memory BM25 + disk persist | Zero infrastructure, survives restarts | Not horizontally scalable without shared storage |
| PyMuPDF extraction | Fast, accurate for text PDFs | No OCR — scanned/image PDFs produce empty text |
| Three-layer grounding | Low hallucination rate | Occasionally over-refuses borderline queries |
| JSON citation format | Machine-parseable, auditable | Requires retry logic when model skips citations |

### Known limitations

- **Scanned PDFs** — image-only PDFs produce no extractable text. All queries will be refused.
- **Large PDFs (200+ pages)** — indexing is fast (BM25 only), but the 50 MB upload limit and memory for PyMuPDF extraction apply.
- **Vocabulary mismatch (residual)** — CRAG corrects one rewrite cycle. Highly unusual phrasing may still miss the target after one correction.
- **Session eviction** — no TTL is enforced. Long-running instances accumulate `chunks.json` files on disk.
- **No streaming** — LLM responses are buffered and returned as a single HTTP response.
- **Groq rate limit** — CRAG-corrected queries use up to 5 API calls; heavy usage approaches the 14,400/day free limit faster than single-call RAG.

---

## 4. Configuration Reference

All tuneable constants live in [backend/config.py](backend/config.py):

| Constant | Default | Effect |
|---|---|---|
| `LLM_MODEL` | `llama-3.1-8b-instant` | Groq model for all LLM calls |
| `LLM_TEMPERATURE` | `0.0` | Deterministic output |
| `CHUNK_MAX_TOKENS` | `800` | Max tokens per chunk |
| `CHUNK_OVERLAP_TOKENS` | `150` | Overlap between chunks |
| `CHUNK_MIN_TOKENS` | `50` | Discard chunks smaller than this |
| `TOP_K` | `5` | Chunks retrieved per BM25 query |
| `MAX_CITATION_RETRIES` | `2` | Layer 3 retry count |
| `MAX_PDF_SIZE_MB` | `50` | Upload size limit |
