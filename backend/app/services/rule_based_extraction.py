"""
Rule-based (regex) extraction of grading weights, dates, and assignment
names from raw syllabus text.

This exists as a deliberate baseline: before reaching for HF models (Table QA,
Document QA, zero-shot classification), we want a working, cheap, and fast
extractor to (a) validate the end-to-end pipeline and (b) have a floor to
measure ML-based improvements against in the eval harness. If regex alone
gets us to 70% accuracy, that tells us something different than if it gets
us to 20%.

Known limitations (expected — this is why we'll layer in ML models next):
- Assumes "Name: X%" or "Name X%" patterns for weights; won't catch tables
  rendered as actual PDF tables with separate columns
- Date parsing is US-format-biased ("Month Day, Year")
- No confidence scoring beyond "did the regex match"
"""

import os
import re
from datetime import date, datetime

from app.models.schemas import AssignmentType, ExtractedAssignment

# Zero-shot classification (via transformers) is opt-in, not default: it
# pulls in torch + a ~1.6GB model download, which is a heavy default for
# anyone just running the regex baseline or the eval harness in CI. Set
# SYLLABUSSYNC_USE_ZERO_SHOT=1 to enable it.
USE_ZERO_SHOT_CLASSIFIER = os.environ.get("SYLLABUSSYNC_USE_ZERO_SHOT") == "1"

# Matches lines like "Midterm Exam: 25%" or "Homework Assignments 20%".
# The name group excludes newlines explicitly (not just via non-greedy
# matching) because \s matches \n too, which previously let the match
# bleed across line boundaries and swallow the preceding line's text.
WEIGHT_PATTERN = re.compile(
    r"^(?P<name>[A-Za-z][A-Za-z ]+?)[:\s]+(?P<weight>\d{1,3}(?:\.\d+)?)\s*%",
    re.MULTILINE,
)

# Matches "September 15, 2026" / "Sep 15 2026" style dates
DATE_PATTERN = re.compile(
    r"(?P<month>January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(?P<day>\d{1,2}),?\s+(?P<year>\d{4})"
)

TYPE_KEYWORDS = {
    AssignmentType.exam: ["exam", "midterm", "final"],
    AssignmentType.quiz: ["quiz"],
    AssignmentType.homework: ["homework", "assignment", "problem set", "hw"],
    AssignmentType.project: ["project"],
    AssignmentType.participation: ["participation", "attendance"],
}

# Common phrasings like "Recitation is worth 10%" or "Attendance counts for 5%"
# have no colon to anchor on, so WEIGHT_PATTERN's name group greedily captures
# the whole run-on sentence fragment up to the number. This strips those known
# filler phrases from the tail of a captured name after the fact, rather than
# trying to make the regex itself smarter (which risks under-matching instead).
NAME_FILLER_SUFFIXES = [
    " is worth",
    " are worth",
    " counts for",
    " accounts for",
    " will be worth",
    " weighs",
    " is",
]


def clean_extracted_name(name: str) -> str:
    for suffix in NAME_FILLER_SUFFIXES:
        if name.lower().endswith(suffix):
            return name[: -len(suffix)].strip()
    return name.strip()


def classify_type(name: str) -> AssignmentType:
    name_lower = name.lower()
    for assignment_type, keywords in TYPE_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return assignment_type
    return AssignmentType.other


def extract_weights(text: str) -> list[ExtractedAssignment]:
    """
    Finds "Name: XX%" style lines and turns them into ExtractedAssignment
    objects.

    Type classification and confidence: by default uses keyword matching
    with a fixed 0.5 confidence (the original baseline — see module
    docstring). If SYLLABUSSYNC_USE_ZERO_SHOT=1, uses a real NLI-based
    zero-shot classifier instead, which also gives a real per-assignment
    confidence score instead of the constant 0.5 — meaning needs_review
    thresholding becomes meaningful for the type field specifically, not
    just a placeholder. Weight/date extraction are unaffected either way;
    this only changes how the *type* field and its confidence are derived.
    """
    assignments = []
    for match in WEIGHT_PATTERN.finditer(text):
        name = clean_extracted_name(match.group("name"))
        weight = float(match.group("weight"))

        # Filter out obvious false positives like "10% per day" late-policy lines
        if "per day" in match.group(0).lower() or "late" in name.lower():
            continue

        if USE_ZERO_SHOT_CLASSIFIER:
            from app.services.zero_shot_classifier import classify_type_zero_shot

            assignment_type, confidence = classify_type_zero_shot(name)
        else:
            assignment_type = classify_type(name)
            confidence = 0.5

        assignments.append(
            ExtractedAssignment(
                name=name,
                type=assignment_type,
                weight_pct=weight,
                due_date=None,
                raw_source_text=match.group(0).strip(),
                confidence=confidence,
            )
        )
    return assignments


def extract_dates(text: str) -> list[tuple[date, str]]:
    """
    Returns (date, surrounding_context) pairs for every date-like string found.
    Downstream logic matches these against assignment names by proximity.
    """
    results = []
    for match in DATE_PATTERN.finditer(text):
        try:
            parsed = datetime.strptime(
                f"{match.group('month')} {match.group('day')} {match.group('year')}",
                "%B %d %Y",
            ).date()
        except ValueError:
            continue

        line_start = text.rfind("\n", 0, match.start()) + 1
        line_end = text.find("\n", match.end())
        if line_end == -1:
            line_end = len(text)
        context = text[line_start:line_end].strip()

        results.append((parsed, context))
    return results


def merge_dates_into_assignments(
    assignments: list[ExtractedAssignment], dates: list[tuple[date, str]]
) -> list[ExtractedAssignment]:
    """
    Naive proximity match: if an assignment's name appears in a date's
    context line, attach that date. This will miss cases where the
    schedule section names assignments slightly differently than the
    grading table does (e.g. "Homework 1" vs "Homework Assignments") —
    a known gap the eval harness should surface.
    """
    for parsed_date, context in dates:
        context_lower = context.lower()
        for assignment in assignments:
            # crude token overlap: first word of the assignment name
            first_word = assignment.name.split()[0].lower()
            if first_word in context_lower and assignment.due_date is None:
                assignment.due_date = parsed_date
                assignment.raw_source_text += f" | schedule: {context}"
    return assignments
