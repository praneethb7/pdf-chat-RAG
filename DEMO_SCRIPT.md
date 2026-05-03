# Demo Script — PDF Chat

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

> "This is PDF Chat — a document assistant that answers questions grounded strictly in the content of your uploaded PDF. It never guesses and never uses outside knowledge."

1. Show the full app in its empty state.
2. Point to the disabled chat input: "No PDF loaded — chat is disabled."

---

## Scene 2 — Upload & Indexing (0:30–1:00)

**Show:** Drag-and-drop → status badge → ready.

1. Drag a PDF onto the upload zone.
2. Watch the upload card appear: filename, page count.
3. Wait for the "Ready" status (2–10 seconds).

> "When you upload a PDF, the backend extracts text page-by-page using PyMuPDF, splits it into overlapping 800-token chunks, and embeds each chunk into a vector using a local sentence-transformers model. Everything runs on the server — no third-party embedding API."

---

## Scene 3 — Grounded Answer with Citations (1:00–2:00)

**Show:** Factual question → answer → citation expand → RAG trace.

1. Type a specific factual question you know the answer to.
2. Press Enter; watch the loading indicator.
3. Answer appears — point out the page citation chip.
4. Click the citation chip to expand the source snippet.
5. Click **"Why this answer?"** to open the RAG trace drawer.
6. Show the similarity scores: "These are the top 5 chunks the model had access to when forming its answer."

> "The model cannot see any part of the PDF except these five retrieved chunks."

---

## Scene 4 — Summary / Meta Query (2:00–2:30)

**Show:** "Summarise in 5 points" works correctly.

1. Type: `Summarise in 5 points` and press Enter.
2. A structured summary appears with citations.

> "Broad questions like 'summarise' don't embed well against specific passages, so the system detects them as document-level queries and retrieves context from across the whole PDF rather than refusing."

---

## Scene 5 — Out-of-Scope Refusal (2:30–3:15)

**Show:** The grounding gate refusing a question the PDF can't answer.

1. Type: `What is the current stock price?` and press Enter.
2. The refusal message appears; citations are empty.

> "There are three independent grounding layers. First, if the similarity search scores are too low, the query is refused without calling the LLM at all — saving cost and latency. If chunks pass the threshold but the model can't extract an answer, it emits grounded=false. Finally, if a model returns an answer without citations, it's retried before being refused."

---

## Scene 6 — Replace Document (3:15–3:45)

**Show:** Swapping PDFs creates an isolated new session.

1. Click **"Replace document"**.
2. Upload a second, different PDF.
3. Ask the same factual question from Scene 3 — show the answer is now about the new document (or refused if it doesn't contain that information).

> "Each upload creates a completely isolated session. There's no cross-contamination between documents."

---

## Scene 7 — Wrap-Up (3:45–4:30)

> "React frontend, FastAPI backend, PyMuPDF for text extraction, sentence-transformers for local embeddings, FAISS for vector search, and Groq's Llama for generation. The entire stack is free — no OpenAI, no paid API. Every answer is traceable to a specific passage in your document, or it's refused."
