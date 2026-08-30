"""
Tests for document_qa.py.

test_parse_date_from_answer_* run against real logic (no model needed).
test_find_due_date_via_qa_* stub out _get_qa_pipeline() — same scope
boundary as the other ML-adjacent test files. See document_qa.py's module
docstring for the honest status of real accuracy.
"""

from datetime import date
from unittest.mock import patch

from app.services.document_qa import _parse_date_from_answer, find_due_date_via_qa


def test_parse_date_from_answer_valid_date():
    assert _parse_date_from_answer("September 15, 2026") == date(2026, 9, 15)


def test_parse_date_from_answer_date_embedded_in_sentence():
    assert _parse_date_from_answer("It's due September 15, 2026 at midnight") == date(2026, 9, 15)


def test_parse_date_from_answer_no_date_present():
    assert _parse_date_from_answer("sometime next week") is None


def test_parse_date_from_answer_invalid_calendar_date():
    """February 30th doesn't exist — must not crash, must return None."""
    assert _parse_date_from_answer("February 30, 2026") is None


def test_parse_date_from_answer_empty_string():
    assert _parse_date_from_answer("") is None


def _fake_qa_pipeline_with_date(question, context):
    return {"answer": "the deadline is September 15, 2026", "score": 0.82}


def _fake_qa_pipeline_no_date(question, context):
    return {"answer": "sometime soon", "score": 0.3}


def test_find_due_date_via_qa_returns_parsed_date_and_score():
    with patch(
        "app.services.document_qa._get_qa_pipeline",
        return_value=_fake_qa_pipeline_with_date,
    ):
        result_date, confidence = find_due_date_via_qa("Homework 1", "some document text")

    assert result_date == date(2026, 9, 15)
    assert confidence == 0.82


def test_find_due_date_via_qa_returns_zero_confidence_when_unparseable():
    """
    A confident-sounding but non-date answer must come back as 0.0
    confidence, not the model's own (possibly high) score — so a bad
    answer can never accidentally look trustworthy to the caller's
    review-threshold check.
    """
    with patch(
        "app.services.document_qa._get_qa_pipeline",
        return_value=_fake_qa_pipeline_no_date,
    ):
        result_date, confidence = find_due_date_via_qa("Homework 1", "some document text")

    assert result_date is None
    assert confidence == 0.0


def test_find_due_date_via_qa_handles_pipeline_exception():
    def raising_pipeline(question, context):
        raise ValueError("simulated model failure")

    with patch("app.services.document_qa._get_qa_pipeline", return_value=raising_pipeline):
        result_date, confidence = find_due_date_via_qa("Homework 1", "some text")

    assert result_date is None
    assert confidence == 0.0
