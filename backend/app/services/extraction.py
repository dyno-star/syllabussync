"""
Syllabus extraction pipeline.

Current status: PDF -> text (pdf_parser.py) -> regex-based weight/date
extraction (rule_based_extraction.py) -> ExtractedSyllabus.

This regex baseline is intentional — see rule_based_extraction.py for why.
Next steps (each should be validated against app/eval/ before replacing
the regex baseline, not alongside it without comparison):

  3. Table QA model over the grading table -> more robust weight extraction
  4. Document QA / NER over the schedule section -> more robust date extraction
  5. Zero-shot classification -> assignment type, replacing the keyword matcher
  6. Real per-field confidence scoring instead of the fixed 0.5 placeholder
"""

from app.models.schemas import ExtractedSyllabus
from app.services.docx_parser import extract_text as extract_docx_text
from app.services.pdf_parser import extract_text as extract_pdf_text
from app.services.rule_based_extraction import (
    extract_dates,
    extract_weights,
    merge_dates_into_assignments,
)

# Below this confidence, we flag the whole syllabus for human review rather
# than silently showing possibly-wrong data.
REVIEW_THRESHOLD = 0.7

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DOTX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.template"


def extract_syllabus(file_bytes: bytes, filename: str, content_type: str = "") -> ExtractedSyllabus:
    is_docx = content_type == DOCX_CONTENT_TYPE or filename.lower().endswith(".docx")
    is_dotx = content_type == DOTX_CONTENT_TYPE or filename.lower().endswith(".dotx")

    try:
        if is_docx or is_dotx:
            text = extract_docx_text(file_bytes, is_template=is_dotx)
        else:
            text = extract_pdf_text(file_bytes)
    except ValueError:
        # No extractable text (scanned PDF, corrupt file, etc.) — return an
        # empty result flagged for review rather than crashing the request.
        return ExtractedSyllabus(assignments=[], needs_review=True)

    assignments = extract_weights(text)
    dates = extract_dates(text)
    assignments = merge_dates_into_assignments(assignments, dates)

    needs_review = (
        len(assignments) == 0
        or any(a.confidence < REVIEW_THRESHOLD for a in assignments)
    )

    return ExtractedSyllabus(
        assignments=assignments,
        needs_review=needs_review,
    )
