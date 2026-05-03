# Multi-Language Support

PDF Chat can retrieve relevant passages in languages other than English, but with important caveats about the embedding model in use.

---

## Embedding Model

The default embedding model is `all-MiniLM-L6-v2` (sentence-transformers). This model is **primarily English-optimised**. It was trained on English corpora and has limited cross-lingual capability.

For stronger multilingual support, swap the model in [backend/config.py](backend/config.py):

```python
EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"
```

This model is purpose-built for multilingual retrieval and maps semantically equivalent sentences across 50+ languages to nearby points in the same embedding space. It is ~420 MB (vs ~90 MB for the default) and slightly slower to encode.

---

## How Cross-Lingual Retrieval Works

With a multilingual model:

```
embed("What is the main finding?")           → [0.12, -0.43, 0.87, ...]
embed("¿Cuál es el hallazgo principal?")     → [0.13, -0.41, 0.85, ...]  # ≈ same
embed("Quelle est la conclusion principale?") → [0.11, -0.44, 0.88, ...]  # ≈ same
```

A Spanish question lands near the same English passage vectors that contain the answer. FAISS returns those passages normally.

---

## LLM Response Language

Groq's `llama-3.1-8b-instant` detects the language of the question and responds in the same language by default, even when the retrieved context is in English.

Example:
```
PDF language: English
Question: "¿Cuál es el hallazgo principal?"
→ Retrieves English chunks (via multilingual embedding)
→ Answers in Spanish, citing English source passages
```

---

## Grounding Is Language-Agnostic

The grounding gates operate on numbers (cosine similarity scores) and JSON structure — not language. A non-English question that finds no relevant passages will be refused in the same language as the question.

---

## Supported Language Combinations (with multilingual model)

| PDF Language | Query Language | Works? |
|---|---|---|
| English | English | ✅ |
| English | Spanish / French / German | ✅ |
| English | Chinese / Japanese / Korean | ✅ |
| Spanish | English | ✅ |
| Any | Any (major world language) | ✅ |

With the default `all-MiniLM-L6-v2`, cross-lingual retrieval works inconsistently. For production multilingual use, switch to `paraphrase-multilingual-MiniLM-L12-v2`.
