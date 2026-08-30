"""
Integration test for the SYLLABUSSYNC_USE_DOCUMENT_QA toggle in
extraction.py. Companion to test_document_qa.py's unit tests — this proves
the toggle actually wires the fallback into the real pipeline, using a
case regex proximity-matching (merge_dates_into_assignments) genuinely
can't solve: an assignment name that doesn't appear near any date in the
text at all.
"""

from datetime import date
from unittest.mock import patch


def _fake_qa_with_date(question, context):
    return {"answer": "September 15, 2026", "score": 0.75}


def test_document_qa_fills_in_date_regex_proximity_matching_missed(monkeypatch):
    monkeypatch.setenv("SYLLABUSSYNC_USE_DOCUMENT_QA", "1")

    import importlib
    from app.services import extraction

    importlib.reload(extraction)

    # Deliberately no date anywhere near "Homework" in this text — regex
    # proximity matching in merge_dates_into_assignments can't find one,
    # so due_date stays None after the regular pipeline runs. The real
    # date is present in the text, just not adjacent to the assignment
    # name — exactly the case QA (which reasons over the whole document,
    # not just nearby lines) is meant to help with.
    fake_text = "Homework: 20%\n\nSome unrelated paragraph.\n\nSeptember 15, 2026 is a Tuesday."

    with patch(
        "app.services.extraction.extract_pdf_text", return_value=fake_text
    ), patch("app.services.extraction.extract_pdf_tables", return_value=[]), patch(
        "app.services.document_qa._get_qa_pipeline", return_value=_fake_qa_with_date
    ):
        result = extraction.extract_syllabus(b"fake pdf bytes", filename="test.pdf")

    assert len(result.assignments) == 1
    assert result.assignments[0].due_date == date(2026, 9, 15)
    assert "via QA" in result.assignments[0].raw_source_text

    monkeypatch.delenv("SYLLABUSSYNC_USE_DOCUMENT_QA", raising=False)
    importlib.reload(extraction)


def test_document_qa_toggle_off_leaves_date_missing(monkeypatch):
    """Default (toggle-off) behavior: unmatched dates stay None, as before."""
    monkeypatch.delenv("SYLLABUSSYNC_USE_DOCUMENT_QA", raising=False)

    import importlib
    from app.services import extraction

    importlib.reload(extraction)

    fake_text = "Homework: 20%\n\nSeptember 15, 2026 is a Tuesday."

    with patch(
        "app.services.extraction.extract_pdf_text", return_value=fake_text
    ), patch("app.services.extraction.extract_pdf_tables", return_value=[]):
        result = extraction.extract_syllabus(b"fake pdf bytes", filename="test.pdf")

    assert len(result.assignments) == 1
    assert result.assignments[0].due_date is None


def test_document_qa_respects_minimum_confidence(monkeypatch):
    """A low-confidence QA answer should NOT be trusted over leaving it blank."""
    monkeypatch.setenv("SYLLABUSSYNC_USE_DOCUMENT_QA", "1")

    import importlib
    from app.services import extraction

    importlib.reload(extraction)

    def low_confidence_qa(question, context):
        return {"answer": "September 15, 2026", "score": 0.1}  # below the 0.3 floor

    fake_text = "Homework: 20%\n\nSeptember 15, 2026 is a Tuesday."

    with patch(
        "app.services.extraction.extract_pdf_text", return_value=fake_text
    ), patch("app.services.extraction.extract_pdf_tables", return_value=[]), patch(
        "app.services.document_qa._get_qa_pipeline", return_value=low_confidence_qa
    ):
        result = extraction.extract_syllabus(b"fake pdf bytes", filename="test.pdf")

    assert result.assignments[0].due_date is None

    monkeypatch.delenv("SYLLABUSSYNC_USE_DOCUMENT_QA", raising=False)
    importlib.reload(extraction)
