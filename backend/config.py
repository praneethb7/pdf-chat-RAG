import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

LLM_MODEL: str = "llama-3.1-8b-instant"
LLM_TEMPERATURE: float = 0.0


CHUNK_MAX_TOKENS: int = 800
CHUNK_OVERLAP_TOKENS: int = 150
CHUNK_MIN_TOKENS: int = 50

TOP_K: int = 5

# Cosine similarity threshold below which the answer is refused (0–1 scale).
# 0.40 is intentionally conservative to keep hallucination risk near zero.
SIMILARITY_THRESHOLD: float = 0.05

# How many times to re-call the LLM when it returns grounded=true but no citations
MAX_CITATION_RETRIES: int = 2

MAX_PDF_SIZE_MB: int = 50
STORAGE_DIR: str = os.path.join(os.path.dirname(__file__), "storage")
UPLOAD_DIR: str = os.path.join(os.path.dirname(__file__), "uploads")
PORT: int = int(os.getenv("PORT", "3001"))
CORS_ORIGIN: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
