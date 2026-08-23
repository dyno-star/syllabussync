"""
Tests for table_extraction.py — the deterministic (non-ML) table reader.

Unlike test_zero_shot_classifier.py, these tests run against real logic,
not stubs — no network or model weights needed, since this whole module is
plain Python regex/matching. If these fail, something is actually broken.
"""

from pathlib import Path

from app.services.docx_parser import extract_tables as extract_docx_tables
from app.services.pdf_parser import extract_tables as extract_pdf_tables
from app.services.table_extraction import (
    extract_assignments_from_table,
    extract_assignments_from_tables,
)

FIXTURES_DIR = Path(__file__).parent.parent / "app" / "eval" / "fixtures"


def test_table_with_real_header_row():
    table = [
        ["Assignment", "Weight"],
        ["Homework", "20%"],
        ["Midterm Exam", "25%"],
    ]
    result = extract_assignments_from_table(table)

    assert len(result) == 2
    assert result[0].name == "Homework"
    assert result[0].weight_pct == 20.0
    assert result[0].confidence == 0.75  # real-header confidence


def test_table_with_no_header_row_uses_positional_fallback():
    """
    Regression test for a real bug: a table with no header row, where the
    first data row happened to contain header-like words ("Homework
    Assignments" contains "assignment"; "20%" contains "%"), used to get
    misread as a header and silently dropped.
    """
    table = [
        ["Homework Assignments", "20%"],
        ["Midterm Exam", "25%"],
        ["Final Exam", "30%"],
    ]
    result = extract_assignments_from_table(table)

    assert len(result) == 3
    names = [a.name for a in result]
    assert "Homework Assignments" in names
    assert all(a.confidence == 0.65 for a in result)  # fallback confidence


def test_grade_scale_table_does_not_false_positive():
    """
    Regression test for a real bug: a letter-grade scale table ("A+" |
    "98-100") used to get misread as assignments worth 98% weight, because
    the weight pattern matched bare numbers without requiring a "%" sign.
    """
    table = [
        ["A+", "98-100"],
        ["A", "93-97"],
        ["A-", "90-92"],
    ]
    result = extract_assignments_from_table(table)

    assert result == []


def test_docx_fixture_extracts_correctly():
    """Full pipeline: real .docx file -> structured tables -> assignments."""
    with open(FIXTURES_DIR / "table_grading_cs260.docx", "rb") as f:
        tables = extract_docx_tables(f.read())

    assignments = extract_assignments_from_tables(tables)

    assert len(assignments) == 3
    weights = {a.name: a.weight_pct for a in assignments}
    assert weights["Homework Assignments"] == 20.0
    assert weights["Midterm Exam"] == 25.0
    assert weights["Final Exam"] == 30.0


def test_civc101_pdf_produces_no_false_positives():
    """
    Full pipeline against the real CIVC 101 PDF, which has multiple tables
    (grade scale, schedule, contacts) but NO real grading-weight table —
    its weights are in prose. This should find nothing, not misfire on
    the grade-scale or schedule tables.
    """
    with open(FIXTURES_DIR / "civc101_real_syllabus.pdf", "rb") as f:
        tables = extract_pdf_tables(f.read())

    assignments = extract_assignments_from_tables(tables)

    assert assignments == []
