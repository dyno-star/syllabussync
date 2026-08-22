"""
Zero-shot assignment-type classification using a pretrained NLI model via
Hugging Face transformers, as a swap-in upgrade for the keyword-matching
classify_type() in rule_based_extraction.py.

Model choice: facebook/bart-large-mnli — the standard baseline model for
HF's zero-shot-classification pipeline. No fine-tuning required since we're
just checking which candidate label the assignment name best entails.
~1.6GB download on first run.

IMPORTANT — sandboxed dev note: this module could not be exercised against
the real model in the environment these commits were authored in, because
that sandbox's network egress does not allow huggingface.co. The
integration (data flow, thresholding, fallback behavior) was verified with
a stubbed pipeline function — see test_zero_shot_classifier.py — not with
real model inference. The actual accuracy improvement over the keyword
baseline needs to be measured by running `python -m app.eval.run_eval`
somewhere with real network access to Hugging Face Hub. Don't trust any
accuracy claim about this specific module until that's been run for real.
"""

from functools import lru_cache

from app.models.schemas import AssignmentType

# Candidate labels phrased as short descriptive phrases, since NLI-based
# zero-shot classification works by checking "this text entails {label}"
# for each candidate — more natural phrasing tends to score better than
# bare category names.
CANDIDATE_LABELS: dict[AssignmentType, str] = {
    AssignmentType.exam: "exam or test",
    AssignmentType.quiz: "quiz",
    AssignmentType.homework: "homework or problem set",
    AssignmentType.project: "project",
    AssignmentType.participation: "attendance or class participation",
    AssignmentType.other: "other graded activity",
}


@lru_cache(maxsize=1)
def _get_classifier():
    """
    Lazily loads the HF pipeline on first use, not at module import time.
    Importing this module (e.g. for the eval harness, or during test
    collection) should never trigger a multi-GB model download as a side
    effect — only actually calling classify_type_zero_shot() should.
    """
    from transformers import pipeline

    return pipeline("zero-shot-classification", model="facebook/bart-large-mnli")


def classify_type_zero_shot(assignment_name: str) -> tuple[AssignmentType, float]:
    """
    Returns (predicted_type, confidence) using zero-shot NLI classification.

    Unlike the regex baseline's fixed 0.5 confidence placeholder, this
    returns the model's own top-label score — a real signal the
    needs_review threshold in extraction.py can act on meaningfully,
    rather than a constant that can never trip the threshold either way.
    """
    classifier = _get_classifier()
    labels = list(CANDIDATE_LABELS.values())
    result = classifier(assignment_name, candidate_labels=labels)

    top_label = result["labels"][0]
    top_score = result["scores"][0]

    label_to_type = {v: k for k, v in CANDIDATE_LABELS.items()}
    predicted_type = label_to_type[top_label]

    return predicted_type, top_score
