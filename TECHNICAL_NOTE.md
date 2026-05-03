# Technical Note — PDF Chat

## 1. Architecture Overview

PDF Chat is a full-stack RAG (Retrieval-Augmented Generation) application. At upload time the PDF is converted into a searchable FAISS vector index; at query time the most relevant passages are retrieved and the LLM is constrained to answer only from those passages.

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
│  ┌──────────────┐               ┌───────────────────────────┐     │
│  │  PyMuPDF     │               │  answer_question()         │     │
│  │  text extract│               │                            │     │
│  │      ▼       │               │  1. FAISS search (top-5)   │     │
│  │  Token-window│               │  2. meta-query gate        │     │
│  │  chunker     │               │  3. similarity threshold   │     │
│  │  (800/150)   │               │  4. build context string   │     │
│  │      ▼       │               │  5. Groq LLM call          │     │
│  │  sentence-   │               │  6. parse JSON + citations │     │
│  │  transformers│               │  7. citation-retry loop    │     │
│  │      ▼       │               └───────────────────────────┘     │
│  │  FAISSStore  │◄──── sessionId ─────────┘                       │
│  └──────────────┘                                                  │
│         │                                                          │
│  In-memory dict {sessionId: FAISSStore}  +  disk persistence      │
└────────────────────────────────────────────────────────────────────┘
```

### Upload pipeline

1. **Text extraction** — PyMuPDF extracts raw text page-by-page, preserving page boundaries for citation attribution.
2. **Chunking** — a custom token-window splitter (tiktoken) creates overlapping 800-token chunks (150-token overlap). Each chunk carries `{ page_num, text }` metadata.
3. **Embedding** — fastembed (ONNX) (`all-MiniLM-L6-v2`) encodes each chunk to a 384-dim L2-normalised vector. Runs entirely locally; no external API call.
4. **Indexing** — vectors are loaded into a FAISS `IndexFlatIP`. Inner product over normalised vectors equals cosine similarity. The index + chunk metadata are persisted to `storage/{sessionId}/`.

### Query pipeline

1. **Embed query** — the question is encoded with the same `all-MiniLM-L6-v2` model.
2. **FAISS search** — top-5 chunks by cosine similarity are returned.
3. **Meta-query gate** — if the question matches a broad pattern (summarise, overview, explain section, key points, etc.) the similarity threshold check is skipped. These queries embed poorly against specific chunks but are clearly document-scoped.
4. **Similarity threshold gate (Layer 1)** — non-meta queries with a top score below `SIMILARITY_THRESHOLD` (0.40) are refused without calling the LLM.
5. **Context assembly** — surviving chunks are concatenated with page labels.
6. **LLM call (Layer 2)** — Groq `llama-3.1-8b-instant` receives a strict system prompt and the context. It must respond with a JSON object containing `grounded`, `answer`, and `citations`.
7. **Citation validation + retry (Layer 3)** — if the model returns `grounded=true` but no citations, the call is retried up to `MAX_CITATION_RETRIES` times with an escalating reminder. After all retries, a refusal is returned.

---

## 2. Design Decisions

### Three-layer grounding gate

Most RAG systems rely solely on the LLM to decide when it doesn't know something. Adding a hard similarity threshold as a pre-LLM filter catches clear out-of-scope queries cheaply (no API call, no latency). The meta-query bypass prevents over-refusal for broad document-level questions. The LLM JSON schema with `grounded: false` is a second independent check for borderline cases. The citation-retry loop is a final guard against uncited confabulation.

### Local embeddings (fastembed + ONNX Runtime)

`all-MiniLM-L6-v2` runs fully in-process via fastembed's ONNX Runtime backend — no PyTorch, no GPU required, ~150 MB footprint. No embedding API cost, no network latency on the hot path, no per-token pricing. The trade-off is that it is primarily an English model — cross-lingual retrieval accuracy is lower than multilingual alternatives like `paraphrase-multilingual-MiniLM-L12-v2`.

### Groq free tier for LLM

`llama-3.1-8b-instant` on Groq's free tier provides 14,400 requests/day with sub-second response times. The trade-off vs. GPT-4o or Claude is reduced instruction-following quality, which is why the JSON output format and citation-retry loop are needed.

### FAISS IndexFlatIP with disk persistence

Sessions survive backend restarts. Each session's index and chunk metadata are written to `storage/{sessionId}/`. On first request after restart the index is loaded from disk and cached in memory. No external vector database is required.

### Token-window chunker parameters

**Chunk size: 800 tokens / Overlap: 150 tokens**

- 800 tokens covers one coherent idea while keeping the embedding signal focused.
- 150-token overlap prevents facts at chunk boundaries from being lost.
- Chunks below `CHUNK_MIN_TOKENS` (50) are discarded to avoid near-empty noise vectors.

### Temperature 0

Fully deterministic output. For a grounded retrieval task, determinism is strictly better than creativity.

---

## 3. Trade-offs

| Decision | Benefit | Cost |
|---|---|---|
| Local embeddings | Free, fast, private | English-optimised; lower cross-lingual accuracy |
| In-memory FAISS + disk persist | Zero infrastructure, survives restarts | Not horizontally scalable without shared storage |
| Groq free LLM | No cost | 14,400 req/day limit; weaker instruction following than GPT-4 |
| PyMuPDF extraction | Fast, accurate for text PDFs | No OCR — scanned/image PDFs produce empty text |
| Three-layer grounding | Low hallucination rate | Occasionally over-refuses borderline queries |
| Meta-query bypass | Handles summary/section questions | Passes all top-5 chunks to LLM regardless of score |
| JSON citation format | Machine-parseable, auditable | Requires retry logic when model skips citations |

### Known limitations

- **Scanned PDFs** — image-only PDFs produce no extractable text. All queries will be refused.
- **Large PDFs (200+ pages)** — indexing can take 15–30 seconds; no progress streaming is implemented.
- **Session eviction** — no TTL is enforced. Long-running instances accumulate indexes on disk.
- **No streaming** — LLM responses are buffered and returned as a single HTTP response.
- **Cross-lingual retrieval** — `all-MiniLM-L6-v2` works best for English. For multilingual use, swap to `paraphrase-multilingual-MiniLM-L12-v2` in `config.py`.

---

## 4. Configuration Reference

All tuneable constants live in [backend/config.py](backend/config.py):

| Constant | Default | Effect |
|---|---|---|
| `LLM_MODEL` | `llama-3.1-8b-instant` | Groq model ID |
| `LLM_TEMPERATURE` | `0.0` | Deterministic output |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | fastembed retrieval model |
| `CHUNK_MAX_TOKENS` | `800` | Max tokens per chunk |
| `CHUNK_OVERLAP_TOKENS` | `150` | Overlap between chunks |
| `CHUNK_MIN_TOKENS` | `50` | Discard chunks smaller than this |
| `TOP_K` | `5` | Chunks retrieved per query |
| `SIMILARITY_THRESHOLD` | `0.15` | Layer 1 refusal threshold |
| `MAX_CITATION_RETRIES` | `2` | Layer 3 retry count |
| `MAX_PDF_SIZE_MB` | `50` | Upload size limit |
