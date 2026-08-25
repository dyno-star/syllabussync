"""
Tests for table_qa.py.

test_table_to_dataframe_* run against real logic (no model needed).
test_extract_assignments_via_table_qa_* stub out _get_table_qa_pipeline(),
same scope boundary as test_zero_shot_classifier.py — these prove the
coordinate-parsing and name-pairing logic is correct, NOT that TAPAS
actually finds the right cells on a real table. See table_qa.py's module
docstring and docs/eval-plan.md for the honest status of real accuracy.
"""

from unittest.mock import patch

import pandas as pd

from app.models.schemas import AssignmentType
from app.services.table_qa import _table_to_dataframe, extract_assignments_via_table_qa


def test_table_to_dataframe_detects_real_header():
    table = [["Assignment", "Weight"], ["Homework", "20%"]]
    df = _table_to_dataframe(table)
    assert list(df.columns) == ["Assignment", "Weight"]
    assert len(df) == 1


def test_table_to_dataframe_generates_placeholder_headers_when_headerless():
    table = [["Homework", "20%"], ["Exam", "25%"]]
    df = _table_to_dataframe(table)
    assert list(df.columns) == ["col_0", "col_1"]
    assert len(df) == 2  # both rows are data, since neither is a header


def test_table_to_dataframe_empty_table():
    assert _table_to_dataframe([]).empty


def _fake_qa_pipeline(table, query):
    """
    Stands in for the real TAPAS pipeline. Returns a fixed answer pointing
    at row 0, column 1 — matching the fake table used in the tests below,
    which is deliberately shaped like ('Homework', '20%').
    """
    return {
        "answer": "20%",
        "coordinates": [(0, 1)],
        "cells": ["20%"],
        "aggregator": "NONE",
    }


def test_extract_assignments_via_table_qa_pairs_name_with_weight():
    table = [["col_0", "col_1"], ["Homework", "20%"]]

    with patch(
        "app.services.table_qa._get_table_qa_pipeline",
        return_value=_fake_qa_pipeline,
    ):
        result = extract_assignments_via_table_qa(table)

    assert len(result) == 1
    assert result[0].name == "Homework"
    assert result[0].weight_pct == 20.0
    assert result[0].type == AssignmentType.homework
    assert result[0].confidence == 0.6


def test_extract_assignments_via_table_qa_returns_empty_for_non_percent_answer():
    """
    If TAPAS's answer cell doesn't contain "%", we don't guess — this
    protects against TAPAS confidently pointing at an unrelated numeric
    cell (a week number, a page reference) that isn't actually a weight.
    """

    def fake_pipeline(table, query):
        return {"answer": "3", "coordinates": [(0, 1)], "cells": ["3"], "aggregator": "NONE"}

    table = [["col_0", "col_1"], ["Week Three", "3"]]

    with patch("app.services.table_qa._get_table_qa_pipeline", return_value=fake_pipeline):
        result = extract_assignments_via_table_qa(table)

    assert result == []


def test_extract_assignments_via_table_qa_handles_pipeline_exception():
    """TAPAS raising on an unparseable table should return [], not crash."""

    def raising_pipeline(table, query):
        raise ValueError("simulated TAPAS failure")

    table = [["col_0", "col_1"], ["Homework", "20%"]]

    with patch("app.services.table_qa._get_table_qa_pipeline", return_value=raising_pipeline):
        result = extract_assignments_via_table_qa(table)

    assert result == []


def test_extract_assignments_via_table_qa_empty_table_short_circuits():
    """An empty or single-column table shouldn't even call the pipeline."""
    with patch("app.services.table_qa._get_table_qa_pipeline") as mock_get:
        result = extract_assignments_via_table_qa([])
        mock_get.assert_not_called()
        assert result == []


def test_extraction_pipeline_falls_back_to_table_qa_when_toggled_on(monkeypatch):
    """
    Confirms SYLLABUSSYNC_USE_TABLE_QA actually gets consulted by
    extract_syllabus when the deterministic header-matcher finds nothing.
    Forces that "finds nothing" condition explicitly (rather than trying
    to construct a table shape the deterministic matcher happens to fail
    on) so this test is testing the toggle-routing logic specifically,
    not table_extraction.py's matching heuristics.
    """
    monkeypatch.setenv("SYLLABUSSYNC_USE_TABLE_QA", "1")

    import importlib
    from app.services import extraction

    importlib.reload(extraction)

    fake_pdf_tables = [[["col_0", "col_1"], ["Homework", "20%"]]]

    with patch(
        "app.services.extraction.extract_assignments_from_tables", return_value=[]
    ), patch("app.services.extraction.extract_pdf_text", return_value="Homework"), patch(
        "app.services.extraction.extract_pdf_tables", return_value=fake_pdf_tables
    ), patch(
        "app.services.table_qa._get_table_qa_pipeline",
        return_value=_fake_qa_pipeline,
    ):
        result = extraction.extract_syllabus(b"fake pdf bytes", filename="test.pdf")

    assert len(result.assignments) == 1
    assert result.assignments[0].name == "Homework"
    assert result.assignments[0].weight_pct == 20.0
    assert result.assignments[0].confidence == 0.6  # table_qa's confidence, not regex's 0.5

    monkeypatch.delenv("SYLLABUSSYNC_USE_TABLE_QA", raising=False)
    importlib.reload(extraction)
