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

USE_TABLE_QA = os.environ.get("SYLLABUSSYNC_USE_TABLE_QA") == "1"
USE_DOCUMENT_QA = os.environ.get("SYLLABUSSYNC_USE_DOCUMENT_QA") == "1"

# Extractive QA's own confidence needs to actually clear this bar to be
# trusted over "just leave it blank" — an answer the model itself wasn't
# confident about isn't better than no answer.
DOCUMENT_QA_MIN_CONFIDENCE = 0.3

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

    if USE_DOCUMENT_QA:
        from app.services.document_qa import find_due_date_via_qa

        for assignment in assignments:
            if assignment.due_date is not None:
                continue
            found_date, confidence = find_due_date_via_qa(assignment.name, text)
            if found_date is not None and confidence >= DOCUMENT_QA_MIN_CONFIDENCE:
                assignment.due_date = found_date
                assignment.raw_source_text += f" | due date via QA (confidence={confidence:.2f})"

    needs_review = (
        len(assignments) == 0
        or any(a.confidence < REVIEW_THRESHOLD for a in assignments)
    )

    return ExtractedSyllabus(
        assignments=assignments,
        needs_review=needs_review,
    )
