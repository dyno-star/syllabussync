"""
Reads grading-weight and due-date info out of structured tables (as
produced by pdf_parser.extract_tables() / docx_parser.extract_tables()),
by matching column headers against known synonyms.

This is deliberately NOT an ML model — it's a second rule-based extractor,
sitting alongside rule_based_extraction.py's text-regex approach, for the
specific case where a syllabus puts its grading breakdown in an actual
table rather than prose. Real Table QA (TAPAS, see table_qa.py) is the
ML upgrade path for tables this simple header-matching can't handle
(irregular structure, merged cells, no clean header row) — but plenty of
real syllabi use simple two/three-column tables where header matching
alone is enough, and it's worth getting that easy case right for free
before reaching for a model.
"""

import re

from app.models.schemas import AssignmentType, ExtractedAssignment
from app.services.rule_based_extraction import classify_type

WEIGHT_HEADER_SYNONYMS = ["weight", "%", "percent", "value", "points"]
NAME_HEADER_SYNONYMS = ["assignment", "category", "name", "component", "item"]

# Matches "20%", "20.5%" — % is required here (unlike the header-detection
# path) specifically to avoid false-positive matches on things like grade
# ranges ("98-100") or arbitrary numbers in unrelated tables. An early
# version of this matched bare numbers too and mis-extracted a letter-grade
# scale table as if "A+" were an assignment worth 98% weight — see
# tests/test_table_extraction.py for that regression case.
CELL_WEIGHT_PATTERN = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")

# Header cells often legitimately contain a bare "%" symbol (e.g. a column
# literally titled "%"), so header detection keeps % optional — this
# separate pattern is only used to decide "does this look like a header
# cell", not to extract a value.
HEADER_WEIGHT_HINT_PATTERN = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%?")


def _find_header_column(header_row: list[str], synonyms: list[str]) -> int | None:
    for i, cell in enumerate(header_row):
        cell_lower = (cell or "").strip().lower()
        if any(syn in cell_lower for syn in synonyms):
            return i
    return None


def _row_looks_like_header(header_row: list[str], weight_col: int) -> bool:
    """
    Guards against the case where a table has no real header row and a
    data row's own contents happen to contain header-like keywords — e.g.
    "Homework Assignments" containing "assignment", or "20%" containing
    "%". A genuine header cell for the weight column should say something
    like "Weight" or "Points", not itself be a parseable percentage —
    if it is, this "header row" is actually the first data row.
    """
    if weight_col >= len(header_row):
        return True
    candidate_weight_cell = (header_row[weight_col] or "").strip()
    return HEADER_WEIGHT_HINT_PATTERN.search(candidate_weight_cell) is None


def _positional_fallback(table: list[list[str | None]]) -> tuple[int, int] | None:
    """
    For tables with no real header row: assume column 0 is the name, and
    pick whichever other column has the highest proportion of cells that
    parse as a weight. Returns (name_col, weight_col) or None if no column
    looks weight-like enough (fewer than half its cells match).
    """
    if not table or len(table[0]) < 2:
        return None

    num_cols = len(table[0])
    best_col, best_ratio = None, 0.0

    for col in range(1, num_cols):
        cells = [row[col] for row in table if col < len(row) and row[col]]
        if not cells:
            continue
        matches = sum(1 for c in cells if CELL_WEIGHT_PATTERN.search(c.strip()))
        ratio = matches / len(cells)
        if ratio > best_ratio:
            best_col, best_ratio = col, ratio

    if best_col is not None and best_ratio >= 0.5:
        return 0, best_col
    return None


def extract_assignments_from_table(table: list[list[str | None]]) -> list[ExtractedAssignment]:
    """
    Given one structured table, tries to find a name column and a weight
    column — first by header row (if there's a real one), falling back to
    positional guessing (column 0 = name, best weight-like column = weight)
    for tables with no header row at all.

    Returns an empty list (not an error) if the table doesn't look like a
    grading table at all. Callers should try multiple tables from a
    document and take whichever produces results, since a syllabus PDF
    often has several unrelated tables (grading scale, schedule, contacts)
    alongside the one that actually matters.
    """
    if len(table) < 1:
        return []

    header_row = table[0]
    name_col = _find_header_column(header_row, NAME_HEADER_SYNONYMS)
    weight_col = _find_header_column(header_row, WEIGHT_HEADER_SYNONYMS)

    has_real_header = (
        name_col is not None
        and weight_col is not None
        and _row_looks_like_header(header_row, weight_col)
    )

    if has_real_header:
        data_rows = table[1:]
    else:
        fallback = _positional_fallback(table)
        if fallback is None:
            return []
        name_col, weight_col = fallback
        data_rows = table  # no header row to skip

    assignments = []
    for row in data_rows:
        if weight_col >= len(row) or name_col >= len(row):
            continue

        name_cell = (row[name_col] or "").strip()
        weight_cell = (row[weight_col] or "").strip()

        if not name_cell or not weight_cell:
            continue

        weight_match = CELL_WEIGHT_PATTERN.search(weight_cell)
        if not weight_match:
            continue

        assignments.append(
            ExtractedAssignment(
                name=name_cell,
                type=classify_type(name_cell),
                weight_pct=float(weight_match.group(1)),
                due_date=None,
                raw_source_text=f"{name_cell} | {weight_cell}",
                # Higher confidence than the regex-on-prose baseline (0.5):
                # a header-matched table cell is a much stronger signal
                # than a regex guess on free text. Positional fallback
                # (no real header found) gets slightly less confidence
                # than a genuine header match, since it's a weaker signal.
                confidence=0.75 if has_real_header else 0.65,
            )
        )

    return assignments


def extract_assignments_from_tables(
    tables: list[list[list[str | None]]],
) -> list[ExtractedAssignment]:
    """
    Tries every table in a document, returns the first one that produces
    any assignments. See extract_assignments_from_table's docstring for
    why "first that works" rather than merging across tables.
    """
    for table in tables:
        result = extract_assignments_from_table(table)
        if result:
            return result
    return []
