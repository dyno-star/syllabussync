"""
Table QA using TAPAS (google/tapas-base-finetuned-wtq) via Hugging Face
transformers — a fallback for tables that table_extraction.py's
deterministic header-matching can't parse (no recognizable header row AND
the positional fallback's weight-column heuristic doesn't clear its 50%
threshold — e.g. a table with merged cells, multi-row headers, or a weight
column mixed with enough non-weight cells to fool the ratio check).

IMPORTANT — sandboxed dev note: same caveat as zero_shot_classifier.py.
This module could not be exercised against the real model in the
environment these commits were authored in (no network access to
huggingface.co from that sandbox). Integration-tested with a stubbed
pipeline (test_table_qa.py), NOT real model inference. Whether this
actually helps on any real syllabus is unmeasured — see docs/eval-plan.md
for how to measure it for real.

Design note on why this is a distinct module from zero_shot_classifier.py
rather than folded together: TAPAS and the zero-shot NLI model are
different model architectures solving different sub-problems (table cell
lookup vs. text classification), loaded and toggled independently, so
someone could reasonably want one without the other.
"""

from functools import lru_cache

import pandas as pd

from app.models.schemas import AssignmentType, ExtractedAssignment
from app.services.rule_based_extraction import classify_type


@lru_cache(maxsize=1)
def _get_table_qa_pipeline():
    """Lazily loaded — see zero_shot_classifier.py for why this matters."""
    from transformers import pipeline

    return pipeline("table-question-answering", model="google/tapas-base-finetuned-wtq")


def _table_to_dataframe(table: list[list[str | None]]) -> pd.DataFrame:
    """
    TAPAS requires a pandas DataFrame of strings with column headers.
    Real syllabi tables often have no usable header row (see
    table_extraction.py's positional-fallback logic for the same problem
    solved differently) — when that's the case here, we generate
    placeholder column names ("col_0", "col_1", ...) and treat every row,
    including the first, as data. TAPAS doesn't need headers to be
    semantically meaningful, just present and consistent.
    """
    if not table:
        return pd.DataFrame()

    num_cols = max(len(row) for row in table)
    normalized_rows = [
        [(cell or "") for cell in row] + [""] * (num_cols - len(row)) for row in table
    ]

    # Heuristic for "does row 0 look like a real header": if none of its
    # cells are purely numeric/percentage, treat it as a header row.
    first_row = normalized_rows[0]
    looks_like_header = not any(
        cell.strip().replace("%", "").replace(".", "").isdigit() for cell in first_row if cell
    )

    if looks_like_header:
        columns = first_row
        data_rows = normalized_rows[1:]
    else:
        columns = [f"col_{i}" for i in range(num_cols)]
        data_rows = normalized_rows

    return pd.DataFrame(data_rows, columns=columns, dtype=str)


def extract_assignments_via_table_qa(
    table: list[list[str | None]],
) -> list[ExtractedAssignment]:
    """
    Asks TAPAS to find grading weights in a table the deterministic
    header-matcher gave up on. Returns an empty list (not an error) if
    TAPAS doesn't find a usable answer — same "fail quiet, let caller try
    the next fallback" contract as table_extraction.py.

    Confidence is fixed at 0.6 rather than passed through from the model's
    own score, deliberately: TAPAS's internal aggregation confidence isn't
    directly comparable to the header-match confidence scale (0.65/0.75)
    used elsewhere, and treating it as if it were would be a false
    precision claim. 0.6 sits below both header-match tiers, reflecting
    that this is a weaker-signal fallback path, not a confident primary
    source — this number is a judgment call, not derived from anything,
    and should be revisited once real accuracy data exists.
    """
    df = _table_to_dataframe(table)
    if df.empty or len(df.columns) < 2:
        return []

    qa = _get_table_qa_pipeline()

    try:
        result = qa(table=df, query="What are the assignment weights?")
    except Exception:
        # TAPAS can raise on tables it genuinely can't handle (too large,
        # no aggregatable numeric column, etc.) — that's a legitimate
        # "no answer" case, not a bug to propagate as a 500.
        return []

    # TAPAS returns cell coordinates for its answer; we still need to pair
    # each identified weight cell with a name from the same row. This
    # walks the answer's cell coordinates rather than trying to parse its
    # free-text "answer" string, since the coordinates are the reliable
    # part of the response.
    assignments = []
    for row_idx, col_idx in result.get("coordinates", []):
        row = df.iloc[row_idx]
        weight_cell = str(row.iloc[col_idx]).strip()
        if "%" not in weight_cell:
            continue

        name_candidates = [str(v).strip() for j, v in enumerate(row) if j != col_idx and str(v).strip()]
        if not name_candidates:
            continue
        name = name_candidates[0]

        try:
            weight = float(weight_cell.replace("%", "").strip())
        except ValueError:
            continue

        assignments.append(
            ExtractedAssignment(
                name=name,
                type=classify_type(name),
                weight_pct=weight,
                due_date=None,
                raw_source_text=f"{name} | {weight_cell} (via Table QA)",
                confidence=0.6,
            )
        )

    return assignments
