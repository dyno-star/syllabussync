"""
Extractive question-answering for due dates, using a standard SQuAD-style
QA model (distilbert-base-cased-distilled-squad) via Hugging Face
transformers.

Scoping note on the name: this is NOT the multi-modal, layout-aware
"Document QA" task (e.g. LayoutLM) that HF's model hub lists under that
name — that variant needs page images and bounding boxes as input, which
our pipeline doesn't have (pdf_parser/docx_parser only extract flat text).
This module asks a text-only extractive QA model a question against the
flattened syllabus text instead. It's a real, useful technique for this
problem, just a lighter-weight one than "Document QA" technically implies —
naming it honestly here so nobody assumes more sophistication than exists.

Used as a fallback specifically for assignments that made it through
extraction (from either the table path or regex path) but ended up with
due_date=None after rule_based_extraction.merge_dates_into_assignments'
proximity-based matching — i.e. "we know this assignment exists and roughly
what it's called, but couldn't find its date by looking at nearby text."

IMPORTANT — sandboxed dev note: same caveat as zero_shot_classifier.py and
table_qa.py. Built and integration-tested with a stubbed pipeline in an
environment without network access to Hugging Face Hub. Real accuracy is
unmeasured — see docs/eval-plan.md.
"""

import re
from datetime import date, datetime
from functools import lru_cache

# Reuses the same month-name date pattern as rule_based_extraction.py, so
# an answer like "September 15, 2026" parses the same way regardless of
# which extraction path found it. Deliberately NOT importing it from
# rule_based_extraction.py to avoid a dependency in the wrong direction —
# this module is a fallback layer, not a peer that module should need to
# know about.
DATE_PATTERN = re.compile(
    r"(?P<month>January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(?P<day>\d{1,2}),?\s+(?P<year>\d{4})"
)


@lru_cache(maxsize=1)
def _get_qa_pipeline():
    """Lazily loaded — see zero_shot_classifier.py for why this matters."""
    from transformers import pipeline

    return pipeline("question-answering", model="distilbert-base-cased-distilled-squad")


def _parse_date_from_answer(answer_text: str) -> date | None:
    """
    The QA model returns a text span, not a structured date — this parses
    whatever it found. Returns None (not an error) for spans that don't
    contain a parseable date, e.g. if the model answers with something
    that isn't actually a date at all (a real failure mode for extractive
    QA on questions it can't actually answer).
    """
    match = DATE_PATTERN.search(answer_text)
    if not match:
        return None

    try:
        return datetime.strptime(
            f"{match.group('month')} {match.group('day')} {match.group('year')}",
            "%B %d %Y",
        ).date()
    except ValueError:
        return None


def find_due_date_via_qa(assignment_name: str, document_text: str) -> tuple[date | None, float]:
    """
    Asks "When is {assignment_name} due?" against the full document text.

    Returns (date_or_None, confidence). Confidence is the QA model's own
    answer-span score when a date was successfully parsed, or 0.0 if
    nothing usable came back — 0.0 specifically (not some other constant)
    so this can never accidentally clear the REVIEW_THRESHOLD check in
    extraction.py and mask a real miss as if it were confident.
    """
    qa = _get_qa_pipeline()

    try:
        result = qa(question=f"When is {assignment_name} due?", context=document_text)
    except Exception:
        return None, 0.0

    parsed_date = _parse_date_from_answer(result.get("answer", ""))
    if parsed_date is None:
        return None, 0.0

    return parsed_date, result.get("score", 0.0)
