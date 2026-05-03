"""
Extract text from a PDF file page-by-page using PyMuPDF.

Returns a list of dicts: [{"page_num": int, "text": str}, ...]
Only pages with meaningful text content are included.
"""

import fitz  # PyMuPDF


def extract_pages(pdf_path: str) -> list[dict]:
    """
    Open the PDF at pdf_path and extract text for each page.

    Returns:
        List of {"page_num": int (1-based), "text": str} for non-empty pages.

    Raises:
        ValueError: if the PDF has no extractable text (e.g. scanned image PDF).
    """
    doc = fitz.open(pdf_path)
    pages: list[dict] = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        text = page.get_text("text")  # plain text with newlines
        text = _clean(text)
        if text:
            pages.append({"page_num": page_index + 1, "text": text})

    doc.close()

    if not pages:
        raise ValueError(
            "No readable text found. The PDF may be a scanned image. "
            "Please use a text-based PDF."
        )

    return pages


def _clean(text: str) -> str:
    """Collapse excessive whitespace while preserving paragraph breaks."""
    import re

    # Normalise line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse runs of blank lines to a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse runs of spaces/tabs (but not newlines)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()
