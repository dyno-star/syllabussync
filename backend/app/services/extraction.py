"""
Syllabus extraction pipeline.

Build order (each step should be independently testable against the
labeled eval set in app/eval/):

  1. PDF -> raw text/layout (unstructured.io or pdfplumber)
  2. Section detection: find the grading table, the schedule/dates section
  3. Table QA model over the grading table -> assignment weights
  4. Document QA / NER over the schedule section -> due dates
  5. Zero-shot classification -> assignment type (exam/homework/project/...)
  6. Confidence scoring -> needs_review flag per field
  7. Assemble into ExtractedSyllabus

For now this returns a stub so the API contract (upload -> ExtractedSyllabus)
is testable end-to-end before any model is wired in.
"""

from app.models.schemas import ExtractedSyllabus


def extract_syllabus(file_bytes: bytes, filename: str) -> ExtractedSyllabus:
    # TODO: replace with real pipeline. Keeping this stub honest (empty,
    # needs_review=True) rather than faking plausible-looking data, so it's
    # obvious in testing that nothing has been extracted yet.
    return ExtractedSyllabus(
        course_code=None,
        course_name=None,
        assignments=[],
        needs_review=True,
    )
