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
    """Finds every (pdf, ground_truth.json) pair in the fixtures dir."""
    pairs = []
    for gt_path in FIXTURES_DIR.glob("*_ground_truth.json"):
        with open(gt_path) as f:
            gt = json.load(f)
        pdf_path = FIXTURES_DIR / gt["source_pdf"]
        if pdf_path.exists():
            pairs.append((pdf_path, gt_path))
        else:
            print(f"WARNING: {gt_path.name} references missing PDF {gt['source_pdf']}")
    return pairs


def score_assignment_match(predicted: dict, expected: dict) -> dict:
    return {
        "name_match": predicted.get("name", "").strip().lower()
        == expected["name"].strip().lower(),
        "type_match": predicted.get("type") == expected["type"],
        "weight_match": predicted.get("weight_pct") == expected["weight_pct"],
        "date_match": predicted.get("due_date") == expected["due_date"],
    }


def run():
    pairs = load_fixture_pairs()
    if not pairs:
        print("No fixtures found in", FIXTURES_DIR)
        return

    totals = {"name_match": 0, "type_match": 0, "weight_match": 0, "date_match": 0}
    total_assignments = 0

    for pdf_path, gt_path in pairs:
        with open(gt_path) as f:
            gt = json.load(f)

        with open(pdf_path, "rb") as f:
            file_bytes = f.read()

        result = extract_syllabus(file_bytes, pdf_path.name)
        predicted_assignments = [a.model_dump(mode="json") for a in result.assignments]
        expected_assignments = gt["assignments"]

        print(f"\n{pdf_path.name}: predicted {len(predicted_assignments)}, "
              f"expected {len(expected_assignments)} assignments")

        # Naive matching by list position — fine for now since our single
        # fixture's assignments come back in source order. Once we have
        # fixtures with reordering issues, switch to name-based matching.
        for predicted, expected in zip(predicted_assignments, expected_assignments):
            scores = score_assignment_match(predicted, expected)
            for key, matched in scores.items():
                totals[key] += int(matched)
            total_assignments += 1
            if not all(scores.values()):
                print(f"  MISMATCH on '{expected['name']}': {scores}")

    print("\n--- Overall accuracy ---")
    for key, count in totals.items():
        pct = (count / total_assignments * 100) if total_assignments else 0
        print(f"  {key}: {count}/{total_assignments} ({pct:.0f}%)")


if __name__ == "__main__":
    run()
