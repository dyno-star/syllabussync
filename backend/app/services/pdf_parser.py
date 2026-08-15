"""
PDF -> raw text extraction.

Kept deliberately separate from the rest of the extraction pipeline so it's
independently testable and swappable. If pdfplumber turns out to struggle on
scanned/image-based syllabi, this is the module to swap for an OCR-based
alternative (e.g. unstructured.io with hi-res mode) without touching the
downstream extraction logic.
"""

import io

import pdfplumber


def extract_text(file_bytes: bytes) -> str:
    """
    Extracts all text from a PDF, page by page, joined with double newlines
    so downstream section-detection logic can reason about page boundaries.

    Raises ValueError if no extractable text is found (e.g. a scanned image
    PDF with no text layer) so callers can decide how to handle that case
    (flag for manual entry, route to OCR, etc.) rather than silently
    returning an empty ExtractedSyllabus.
    """
    text_parts: list[str] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    full_text = "\n\n".join(text_parts).strip()

    if not full_text:
        raise ValueError(
            "No extractable text found in PDF. This may be a scanned/image-only "
            "document that requires OCR."
        )

    return full_text
