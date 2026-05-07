# PDF Chat — Grounded RAG Document Assistant

Upload any PDF and ask questions. Every answer is grounded exclusively in the document's content and comes with page-level citations. Powered by a fully free stack — no paid API required.

---

## Features

- **Strict grounding** — two-layer gate prevents hallucination: cosine-similarity threshold + LLM self-refusal
- **Page citations** — every answer links to the exact source passages
- **Out-of-scope detection** — questions outside the PDF are explicitly refused rather than invented
- **Meta-query support** — broad questions like "summarise" or "explain section A" bypass the similarity gate and retrieve document-wide context
- **100% free** — local embeddings (sentence-transformers) + Groq free-tier LLM (14,400 req/day)
- **RAG trace drawer** — "Why this answer?" toggle reveals raw similarity search results

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Backend | Python 3.11+ · FastAPI · Uvicorn |
| PDF Parsing | PyMuPDF (fitz) |
| Chunking | Custom token-window splitter (tiktoken) |
| Embeddings | `all-MiniLM-L6-v2` via sentence-transformers — runs locally, free |
| Vector DB | FAISS (IndexFlatIP, in-memory) |
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

> **First run:** sentence-transformers will download `all-MiniLM-L6-v2` (~90 MB) once and cache it locally.

---

## Usage

1. **Upload a PDF** — drag and drop onto the left panel, or click to browse (up to 50 MB)
2. **Wait for indexing** — the status badge changes to "Ready" (2–10 seconds depending on PDF size)
3. **Ask a question** — type in the chat box and press Enter
4. **Review citations** — click any citation chip to see the exact source passage
5. **Inspect the RAG trace** — click "Why this answer?" to view raw similarity scores
6. **Replace document** — click "Replace document" to start a new session

---

## Example Queries

| Query | Expected behaviour |
|---|---|
| `"What is the main topic of this document?"` | Grounded answer with citation |
| `"Summarise in 5 points"` | Multi-chunk synthesis with citations |
| `"Explain section A"` | Section-scoped answer |
| `"What does the author recommend for X?"` | Direct answer or citation if mentioned |
| `"What is the capital of France?"` | Out-of-scope refusal |

---

## Project Structure

```
pdf-chat/
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
│   │   ├── embeddings.py  FAISSStore + sentence-transformers
│   │   └── llm.py         Groq integration + grounding logic
│   ├── config.py          All tuneable constants
│   ├── requirements.txt
│   └── tests/             Evaluation suite
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
uvicorn app.main:app --port 3001 &   # start backend
python -m tests.run_evaluation
```

See [backend/TESTING.md](backend/TESTING.md) for the full methodology.
