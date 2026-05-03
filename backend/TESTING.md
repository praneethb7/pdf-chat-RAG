# Evaluation Test Suite

Automated end-to-end evaluation that verifies the RAG pipeline's grounding, citation, and refusal behaviour using a reproducible sample document.

---

## Sample Document

**File:** `tests/fixtures/climatecore_overview.pdf` (auto-generated on first run)
**Topic:** *ClimateCore Platform Technical Overview* — a fictional 5-page cloud-analytics product brief.

| Page | Section | Key facts tested |
|------|---------|-----------------|
| 1 | Introduction | Founder name, HQ, founding year |
| 2 | Core Modules | Number of data sources (47), module names |
| 3 | Technical Architecture | Median API response time (127 ms) |
| 4 | Pricing | Professional plan cost ($249/month) |
| 5 | Security & Compliance | Encryption standard (AES-256), certifications |

---

## Test Cases

### Valid queries — must answer with a citation

| # | Query | Expected behaviour |
|---|-------|--------------------|
| 1 | Who founded ClimateCore? | "Dr. Elena Marchetti"; cites page 1 |
| 2 | How many climate data sources does DataVault integrate? | "47"; cites page 2 |
| 3 | What is the median API response time? | "127 milliseconds"; cites page 3 |
| 4 | How much does the Professional plan cost per month? | "$249"; cites page 4 |
| 5 | What encryption standard is used for data at rest? | "AES-256"; cites page 5 |

### Invalid queries — must refuse (`isOutOfScope: true`)

| # | Query | Why |
|---|-------|-----|
| 6 | What is ClimateCore's current stock price? | No market data in PDF |
| 7 | Who are ClimateCore's main competitors? | Competitor info not mentioned |
| 8 | What is the capital of France? | Completely unrelated |

---

## Running the Tests

### Prerequisites

```bash
cd backend
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r tests/requirements-test.txt
```

Ensure `GROQ_API_KEY` is set in `backend/.env`.

### Start the backend

```bash
uvicorn app.main:app --host 0.0.0.0 --port 3001
```

### Run the full evaluation suite

```bash
# from backend/
python -m tests.run_evaluation
```

### Options

```
--base-url URL          Backend base URL (default: http://localhost:3001)
--skip-chunk-removal    Skip the FAISS rebuild simulation (faster smoke test)
```

### Examples

```bash
# Quick smoke test
python -m tests.run_evaluation --skip-chunk-removal

# Against a deployed backend
BACKEND_URL=https://your-backend.onrender.com python -m tests.run_evaluation
```

---

## Chunk-Removal Simulation

Proves that answers come from the indexed document, not from the LLM's parametric memory:

1. Query `"What is the median API response time?"` against the **full** index.
2. Remove the chunk(s) containing `"127 milliseconds"` from `chunks.json`.
3. Rebuild the FAISS index from the remaining chunks.
4. Re-run the same query.
5. **Expected:** refused (`isOutOfScope: true`) or noticeably vague — proving grounding.

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All 8 test cases passed |
| `1` | One or more test cases failed |

---

## CI Example

```yaml
# .github/workflows/eval.yml
- name: Run evaluation
  run: python -m tests.run_evaluation --skip-chunk-removal
  working-directory: backend
  env:
    GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
```

---

## File Layout

```
backend/tests/
├── __init__.py
├── requirements-test.txt   # requests>=2.31
├── generate_pdf.py         # Creates climatecore_overview.pdf via PyMuPDF
├── test_cases.py           # TestCase dataclasses (8 cases + simulation config)
├── run_evaluation.py       # Main runner
└── fixtures/
    └── climatecore_overview.pdf   # auto-generated on first run
```
