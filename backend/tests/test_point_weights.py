from app.models.schemas import AssignmentType
from app.services.rule_based_extraction import extract_point_weights


def test_extracts_points_headings_on_100_point_scale():
    text = (
        "5. Grading (based on 100-point scale)\n"
        "Engaging with course materials and class participation (50 points)\n"
        "Student participation in each module is worth 10 points (50 total).\n"
        "Journal Entries (20 points)\n"
        "Journal entries are worth 5 points each (20 total).\n"
        "Term-Long Project (30 points)\n"
    )
    result = extract_point_weights(text)

    assert [(a.name, a.weight_pct, a.type) for a in result] == [
        ("Engaging with course materials and class participation", 50.0, AssignmentType.participation),
        ("Journal Entries", 20.0, AssignmentType.homework),
        ("Term-Long Project", 30.0, AssignmentType.project),
    ]


def test_normalizes_non_100_point_totals():
    text = "Homework (200 pts)\nMidterm Exam (150 points)\nFinal Exam (150 points)\n"
    result = extract_point_weights(text)

    assert [a.weight_pct for a in result] == [40.0, 30.0, 30.0]


def test_ignores_points_mentioned_in_prose():
    text = "Each quiz is worth 10 points (50 total) and the lab report (20 points) is due later.\n"
    assert extract_point_weights(text) == []


def test_single_heading_is_not_reported_as_100_percent():
    assert extract_point_weights("Final Project (40 points)\n") == []
