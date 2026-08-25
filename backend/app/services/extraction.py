"""
Syllabus extraction pipeline.

Current status: PDF/docx -> text + structured tables -> assignments.

Two extraction paths, tried in order:
  1. Structured tables (table_extraction.py) — tried first, since a
     header-matched table cell is a stronger signal than a regex guess on
     flattened prose. Used only if it actually finds something; an empty
     result falls through to path 2 rather than being treated as "this
     syllabus has zero assignments."
  1b. Table QA (table_qa.py, TAPAS) — opt-in via SYLLABUSSYNC_USE_TABLE_QA,
      tried on any table path 1 couldn't parse, before falling through to
      regex. See table_qa.py's module docstring for why this is unmeasured
      (no network access to Hugging Face Hub in the sandbox these commits
      were authored in).
  2. Regex-on-text (rule_based_extraction.py) — the original baseline,
     used as a fallback for syllabi that put grading info in prose rather
     than a real table (e.g. CIVC 101 — see app/eval/fixtures).

Due-date extraction currently always runs against the flattened text
(extract_dates), regardless of which path found the assignments — schedule
sections with due dates are usually prose even when the grading breakdown
itself is tabular, so there's no strong reason yet to duplicate date
extraction into the table path too. Worth revisiting once we have a real
fixture where that assumption breaks.

Remaining roadmap (each should be validated against app/eval/ before
replacing the current approach, not alongside it without comparison):

  - Table QA model over tables the header-matcher can't parse (irregular
    structure, no clean header row, merged cells)
  - Document QA / NER over the schedule section -> more robust date
    extraction (see the CIVC 101 schedule-table finding in docs/eval-plan.md)
  - Zero-shot classification -> assignment type (built in
    zero_shot_classifier.py, wired in behind SYLLABUSSYNC_USE_ZERO_SHOT,
    but real accuracy vs. the keyword baseline is still unmeasured)
"""

import os

from app.models.schemas import ExtractedSyllabus
from app.services.docx_parser import extract_tables as extract_docx_tables
from app.services.docx_parser import extract_text as extract_docx_text
from app.services.pdf_parser import extract_tables as extract_pdf_tables
from app.services.pdf_parser import extract_text as extract_pdf_text
from app.services.rule_based_extraction import (
    extract_dates,
    extract_weights,
    merge_dates_into_assignments,
)
from app.services.table_extraction import extract_assignments_from_tables

# Table QA (TAPAS) is opt-in for the same reason zero-shot classification
# is: heavy deps (torch + a model download), not worth forcing on anyone
# just running the deterministic baseline.
USE_TABLE_QA = os.environ.get("SYLLABUSSYNC_USE_TABLE_QA") == "1"

# Below this confidence, we flag the whole syllabus for human review rather
# than silently showing possibly-wrong data.
REVIEW_THRESHOLD = 0.7

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DOTX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.template"


def extract_syllabus(file_bytes: bytes, filename: str, content_type: str = "") -> ExtractedSyllabus:
    is_docx = content_type == DOCX_CONTENT_TYPE or filename.lower().endswith(".docx")
    is_dotx = content_type == DOTX_CONTENT_TYPE or filename.lower().endswith(".dotx")
    is_word = is_docx or is_dotx

    try:
        if is_word:
            text = extract_docx_text(file_bytes, is_template=is_dotx)
            tables = extract_docx_tables(file_bytes, is_template=is_dotx)
        else:
            text = extract_pdf_text(file_bytes)
            tables = extract_pdf_tables(file_bytes)
    except ValueError:
        # No extractable text (scanned PDF, corrupt file, etc.) — return an
        # empty result flagged for review rather than crashing the request.
        return ExtractedSyllabus(assignments=[], needs_review=True)

    assignments = extract_assignments_from_tables(tables)

    if not assignments and USE_TABLE_QA and tables:
        from app.services.table_qa import extract_assignments_via_table_qa

        for table in tables:
            assignments = extract_assignments_via_table_qa(table)
            if assignments:
                break

    if not assignments:
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
