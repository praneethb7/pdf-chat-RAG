# Demo Script — PDF Chat (Corrective RAG)

A step-by-step guide for a 3–5 minute walkthrough. Each section is a distinct scene you can record independently.

---

## Before You Record

**Setup checklist:**
- [ ] Backend running: `cd backend && source .venv/bin/activate && uvicorn app.main:app --port 3001 --reload`
- [ ] Frontend running: `cd frontend && npm run dev`
- [ ] Browser open at `http://localhost:5173`
- [ ] A real PDF ready — a technical doc, research paper, or product spec with specific facts
- [ ] Browser devtools closed, zoom at 100%, window maximised

---

## Scene 1 — Cold Open (0:00–0:30)

**Show:** Empty application state.

> "This is PDF Chat — a document assistant that uses Corrective RAG to answer questions grounded strictly in your uploaded PDF. It never guesses, never uses outside knowledge, and self-corrects its own retrieval when it detects it fetched the wrong passages."

1. Show the full app in its empty state.
2. Point to the disabled chat input: "No PDF loaded — chat is disabled."

---

## Scene 2 — Upload & Indexing (0:30–1:00)

**Show:** Drag-and-drop → status badge → ready.

1. Drag a PDF onto the upload zone.
2. Watch the upload card appear: filename, page count.
3. Wait for the "Ready" status (1–3 seconds).

> "When you upload a PDF, the backend extracts text page-by-page using PyMuPDF, splits it into overlapping 800-token chunks, and builds a BM25 keyword index. No embedding model, no GPU, no cloud ML service — this runs in ~100 MB of RAM and deploys on a free 512 MB server."

---

## Scene 3 — Grounded Answer with Citations (1:00–2:00)

**Show:** Factual question → answer → citation expand → RAG trace.

1. Type a specific factual question you know the answer to.
2. Press Enter; watch the loading indicator.
3. Answer appears — point out the page citation chip.
4. Click the citation chip to expand the source snippet.
5. Click **"Why this answer?"** to open the RAG trace drawer.
6. Show the retrieved passages: "These are the only passages the model had access to."

> "The model cannot see any part of the PDF except these retrieved passages."

---

## Scene 4 — CRAG Correction in Action (2:00–2:45)

**Show:** A query using informal vocabulary — CRAG detects the mismatch and fixes it.

1. Type a question using informal or abbreviated terms. On the Attention paper: `Why is the Transformer better than RNNs?`
2. Show the answer arriving with citations from the correct section.

> "This is Corrective RAG. BM25 initially retrieves chunks about architecture diagrams and results tables — not what we need. A fast LLM evaluator detects the mismatch. It rewrites the query — expanding 'RNNs' to 'recurrent neural networks' and replacing 'better' with 'advantages over' — then re-retrieves. The second pass finds the right section and the answer comes through with citations."

*(Optional: show backend terminal — you'll see `CRAG relevance verdict: irrelevant` → `CRAG rewritten query` → correct chunks retrieved)*

---

## Scene 5 — Summary / Meta Query (2:45–3:15)

**Show:** "Summarise in 5 points" works correctly.

1. Type: `Summarise in 5 points` and press Enter.
2. A structured summary appears with citations.

> "Broad document-level questions skip the CRAG evaluator and retrieve context from across the whole PDF."

---

## Scene 6 — Out-of-Scope Refusal (3:15–3:45)

**Show:** The grounding gate refusing a question the PDF can't answer.

1. Type: `What is the capital of France?` and press Enter.
2. The refusal message appears; citations are empty.

> "BM25 returns zero matching chunks — 'capital' doesn't appear in this PDF. The query is refused before any LLM call is made."

---

## Scene 7 — Replace Document (3:45–4:15)

**Show:** Swapping PDFs creates an isolated new session.

1. Click **"Replace document"**.
2. Upload a second, different PDF.
3. Ask the same factual question from Scene 3 — show the answer is about the new document (or refused if that information isn't there).

> "Each upload is a completely isolated session. No cross-contamination."

---

## Scene 8 — Wrap-Up (4:15–4:45)

> "React frontend, FastAPI backend, PyMuPDF for extraction, BM25 for retrieval, Corrective RAG for self-correcting retrieval, Groq Llama for generation. The entire stack runs on Render's free 512 MB tier. No OpenAI, no paid API, no GPU. Every answer is traceable to a specific passage, or it's refused."
