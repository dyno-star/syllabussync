"""
Runs the extraction pipeline against every fixture in app/eval/fixtures/
and reports per-field accuracy against the ground truth JSON.

Usage:
    cd backend
    python -m app.eval.run_eval

As real (anonymized) syllabi are added to fixtures/, this becomes the
regression check per docs/eval-plan.md — accuracy dropping here should
be treated like a failing test, not a footnote.
"""

import json
from pathlib import Path

from app.services.extraction import extract_syllabus

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture_pairs() -> list[tuple[Path, Path]]:
    """Finds every (source_file, ground_truth.json) pair in the fixtures dir."""
    pairs = []
    for gt_path in FIXTURES_DIR.glob("*_ground_truth.json"):
        with open(gt_path) as f:
            gt = json.load(f)
        # "source_file" is the current field name; "source_pdf" is kept as a
        # fallback for older fixtures written before we supported docx/dotx.
        source_name = gt.get("source_file") or gt.get("source_pdf")
        source_path = FIXTURES_DIR / source_name
        if source_path.exists():
            pairs.append((source_path, gt_path))
        else:
            print(f"WARNING: {gt_path.name} references missing file {source_name}")
    return pairs


def _normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def score_assignment_match(predicted: dict | None, expected: dict) -> dict:
    """
    predicted is None when extraction found no assignment with this name —
    every field then counts as a miss. Without that, a missing assignment
    whose expected due_date is null would score a "correct" date for free.
    """
    if predicted is None:
        return {"name_match": False, "type_match": False, "weight_match": False, "date_match": False}
    return {
        "name_match": True,
        "type_match": predicted.get("type") == expected["type"],
        "weight_match": predicted.get("weight_pct") is not None
        and expected["weight_pct"] is not None
        and abs(predicted["weight_pct"] - expected["weight_pct"]) <= 0.5,
        "date_match": predicted.get("due_date") == expected["due_date"],
    }

def run():
    pairs = load_fixture_pairs()
    if not pairs:
        print("No fixtures found in", FIXTURES_DIR)
        return

    totals = {"name_match": 0, "type_match": 0, "weight_match": 0, "date_match": 0}
    total_assignments = 0
    total_predicted = 0

    for source_path, gt_path in pairs:
        with open(gt_path) as f:
            gt = json.load(f)

        with open(source_path, "rb") as f:
            file_bytes = f.read()

        result = extract_syllabus(file_bytes, source_path.name)
        predicted_assignments = [a.model_dump(mode="json") for a in result.assignments]
        expected_assignments = gt["assignments"]

        print(f"\n{source_path.name}: predicted {len(predicted_assignments)}, "
              f"expected {len(expected_assignments)} assignments")

        # Match by normalized name rather than list position, so one missed
        # or extra row doesn't shift every later comparison. Each predicted
        # row can satisfy at most one expected row.
        unmatched_predicted = list(predicted_assignments)
        for expected in expected_assignments:
            predicted = next(
                (p for p in unmatched_predicted
                 if _normalize_name(p.get("name", "")) == _normalize_name(expected["name"])),
                None,
            )
            if predicted is not None:
                unmatched_predicted.remove(predicted)
            scores = score_assignment_match(predicted, expected)
            for key, matched in scores.items():
                totals[key] += int(matched)
            total_assignments += 1
            if not all(scores.values()):
                print(f"  MISMATCH on '{expected['name']}': {scores}")

        total_predicted += len(predicted_assignments)
        for extra in unmatched_predicted:
            print(f"  EXTRA (not in ground truth): '{extra.get('name')}'")

    print("\n--- Overall accuracy ---")
    for key, count in totals.items():
        pct = (count / total_assignments * 100) if total_assignments else 0
        print(f"  {key}: {count}/{total_assignments} ({pct:.0f}%)")

    # name_match above is recall over expected assignments; precision catches
    # the opposite failure — rows extraction invented that aren't real.
    found = totals["name_match"]
    precision = (found / total_predicted * 100) if total_predicted else 0
    print(f"  precision: {found}/{total_predicted} predicted rows are real ({precision:.0f}%)")


if __name__ == "__main__":
    run()
