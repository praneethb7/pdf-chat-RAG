# PDF Chat — Corrective RAG Document Assistant

Upload any PDF and ask questions. Every answer is grounded exclusively in the document's content and comes with page-level citations. Powered by a fully free stack — no paid API required.

---

## Features

- **Corrective RAG (CRAG)** — if BM25 retrieves the wrong chunks, an LLM evaluator detects the mismatch and rewrites the query (expanding abbreviations, replacing informal terms with academic vocabulary) before re-retrieving
- **Strict grounding** — three-layer gate prevents hallucination: BM25 empty-result gate → CRAG relevance evaluation → LLM self-refusal with `grounded: false`
- **Page citations** — every answer links to the exact source passages
- **Out-of-scope detection** — questions outside the PDF are explicitly refused rather than invented
- **Meta-query support** — broad questions like "summarise" or "explain section A" bypass the CRAG evaluator and retrieve document-wide context
- **100% free** — BM25 retrieval (no local ML model) + Groq free-tier LLM (14,400 req/day)
- **512 MB deployable** — no ONNX runtime, no PyTorch; entire backend fits in Render's free tier
- **RAG trace drawer** — "Why this answer?" toggle reveals raw BM25 retrieval results

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Backend | Python 3.11+ · FastAPI · Uvicorn |
| PDF Parsing | PyMuPDF (fitz) |
| Chunking | Custom token-window splitter (tiktoken) |
| Retrieval | BM25 (rank-bm25) — keyword retrieval, no local ML model |
| Corrective RAG | Groq LLM evaluates chunk relevance; rewrites query if off-target |
| LLM | Groq `llama-3.1-8b-instant` — free tier, 14,400 req/day |

---

## Prerequisites

- Node.js 18+
- Python 3.11+
- A free [Groq API key](https://console.groq.com) (no credit card required)

---

## Setup

### 1. Clone

```bash
git clone https://github.com/praneethb7/pdf-chat-RAG.git
cd pdf-chat-RAG
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Copy and edit the environment file:

```bash
cp .env.example .env
```

```env
# backend/.env
GROQ_API_KEY=gsk_...     # get free key at console.groq.com
PORT=3001
FRONTEND_URL=http://localhost:5173
```

### 3. Frontend

```bash
cd ../frontend
npm install
```

---

## Running Locally

Open **two terminals**:

**Terminal 1 — Backend:**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 3001 --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

## How CRAG Works

Standard RAG retrieves chunks by keyword overlap and passes them directly to the LLM. This fails when the user's question uses different vocabulary than the document — e.g. asking "Why is the Transformer better than RNNs?" when the paper uses "recurrent layers" and "parallelization".

CRAG adds a correction step between retrieval and generation:

```
Question
   │
   ▼
BM25 retrieve top-K chunks
   │
   ▼
LLM evaluator — are these chunks relevant to the question?
   ├── relevant / partial ──► generate answer
   └── irrelevant
           │
           ▼
       LLM rewrites query
       (expands abbreviations, academic vocab)
           │
           ▼
       BM25 re-retrieve with rewritten query
           │
           ▼
       generate answer  (or refuse if still no match)
```

---

## Usage

1. **Upload a PDF** — drag and drop onto the left panel, or click to browse (up to 50 MB)
2. **Wait for indexing** — the status badge changes to "Ready" (1–3 seconds)
3. **Ask a question** — type in the chat box and press Enter
4. **Review citations** — click any citation chip to see the exact source passage
5. **Inspect the RAG trace** — click "Why this answer?" to view BM25 retrieval results
6. **Replace document** — click "Replace document" to start a new session

---

## Example Queries

| Query | Expected behaviour |
|---|---|
| `"What is the main topic of this document?"` | Grounded answer with citation |
| `"Summarise in 5 points"` | Multi-chunk synthesis with citations |
| `"Why is the Transformer better than RNNs?"` | CRAG rewrites → finds Section 4 → cited answer |
| `"What does the author recommend for X?"` | Direct answer or citation if mentioned |
| `"What is the capital of France?"` | Out-of-scope refusal (no BM25 match) |

---

## Project Structure

```
pdf-chat-RAG/
├── frontend/              React + TypeScript UI
│   └── src/
│       ├── components/    ChatWindow, ChatMessage, PDFUpload, CitationBlock, ...
│       ├── lib/           API client, utilities
│       └── types.ts       Shared TypeScript interfaces
├── backend/               Python FastAPI API
│   ├── app/
│   │   ├── main.py        FastAPI app, routes
│   │   ├── pdf_processor.py  PyMuPDF text extraction
│   │   ├── chunker.py     Token-window chunker
│   │   ├── embeddings.py  BM25Store (rank-bm25)
│   │   ├── crag.py        CRAG — relevance evaluator + query rewriter
│   │   └── llm.py         Groq integration + CRAG pipeline + grounding logic
│   ├── config.py          All tuneable constants
│   ├── requirements.txt
│   └── tests/             Evaluation suite
├── .python-version        Pins Python 3.11 for Render deployment
├── README.md
├── TECHNICAL_NOTE.md
├── DEPLOYMENT.md
└── DEMO_SCRIPT.md
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Groq API key (free at console.groq.com) |
| `PORT` | No | `3001` | Uvicorn port |
| `FRONTEND_URL` | No | `http://localhost:5173` | CORS allowed origin |

---

## Evaluation Suite

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --port 3001 &
python -m tests.run_evaluation
```

See [backend/TESTING.md](backend/TESTING.md) for the full methodology.
