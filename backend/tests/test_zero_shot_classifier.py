"""
Tests for the zero-shot classifier integration.

These do NOT test the real facebook/bart-large-mnli model — they stub out
_get_classifier() to return a fake pipeline function, so we can verify the
*integration logic* (label mapping, confidence pass-through, the
extract_weights toggle) without needing network access to Hugging Face Hub
or a multi-GB model download. That's a deliberate scope boundary, not an
oversight: these tests would pass even if the real model's classifications
were nonsense, because they're checking plumbing, not model quality.

Real accuracy against the eval fixtures (app/eval/run_eval.py) must be
measured separately, with SYLLABUSSYNC_USE_ZERO_SHOT=1 and the real
transformers/torch dependencies installed, somewhere with real network
access. See requirements-ml.txt and docs/eval-plan.md.
"""

from unittest.mock import patch

from app.models.schemas import AssignmentType
from app.services.zero_shot_classifier import classify_type_zero_shot, CANDIDATE_LABELS


def _fake_pipeline(text, candidate_labels):
    """
    Stands in for the real HF pipeline callable. Always returns "exam or
    test" as the top label with a fixed confidence, regardless of input —
    good enough to verify label-mapping and confidence pass-through without
    needing real model inference.
    """
    return {
        "labels": ["exam or test"] + [l for l in candidate_labels if l != "exam or test"],
        "scores": [0.87] + [0.02] * (len(candidate_labels) - 1),
    }


def test_classify_type_zero_shot_maps_label_back_to_enum():
    with patch(
        "app.services.zero_shot_classifier._get_classifier",
        return_value=_fake_pipeline,
    ):
        predicted_type, confidence = classify_type_zero_shot("Midterm Exam")

    assert predicted_type == AssignmentType.exam
    assert confidence == 0.87


def test_classify_type_zero_shot_passes_all_candidate_labels():
    """
    The classifier must be given every candidate label, not a subset —
    dropping one silently would bias predictions toward whatever labels
    happen to remain. Verified by inspecting what the stub actually received.
    """
    received_labels = {}

    def recording_pipeline(text, candidate_labels):
        received_labels["labels"] = candidate_labels
        return _fake_pipeline(text, candidate_labels)

    with patch(
        "app.services.zero_shot_classifier._get_classifier",
        return_value=recording_pipeline,
    ):
        classify_type_zero_shot("Homework 1")

    assert set(received_labels["labels"]) == set(CANDIDATE_LABELS.values())


def test_extract_weights_uses_zero_shot_when_toggled_on(monkeypatch):
    """
    Confirms the SYLLABUSSYNC_USE_ZERO_SHOT env var actually routes through
    the zero-shot path in extract_weights, and that the resulting
    confidence is the model's real score — not the hardcoded 0.5 the
    keyword-matching path uses.
    """
    monkeypatch.setenv("SYLLABUSSYNC_USE_ZERO_SHOT", "1")

    # Reload the module so it re-reads the env var — it's read at import
    # time into USE_ZERO_SHOT_CLASSIFIER, not re-checked per call.
    import importlib
    from app.services import rule_based_extraction

    importlib.reload(rule_based_extraction)

    with patch(
        "app.services.zero_shot_classifier._get_classifier",
        return_value=_fake_pipeline,
    ):
        assignments = rule_based_extraction.extract_weights("Midterm Exam: 25%")

    assert len(assignments) == 1
    assert assignments[0].type == AssignmentType.exam
    assert assignments[0].confidence == 0.87  # not the 0.5 keyword-path default

    # Reload again to restore the default (off) state for any tests that
    # run after this one in the same process.
    monkeypatch.delenv("SYLLABUSSYNC_USE_ZERO_SHOT", raising=False)
    importlib.reload(rule_based_extraction)


def test_extract_weights_uses_keyword_baseline_by_default(monkeypatch):
    """Confirms the default (untoggled) path is unaffected — still 0.5 confidence."""
    monkeypatch.delenv("SYLLABUSSYNC_USE_ZERO_SHOT", raising=False)

    import importlib
    from app.services import rule_based_extraction

    importlib.reload(rule_based_extraction)

    assignments = rule_based_extraction.extract_weights("Midterm Exam: 25%")

    assert len(assignments) == 1
    assert assignments[0].type == AssignmentType.exam
    assert assignments[0].confidence == 0.5
