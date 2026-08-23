# Eval Plan: Syllabus Extraction Accuracy

The extraction pipeline is only useful if we can measure how well it works.
This is the piece most "RAG demo" portfolio projects skip — doing it well is
the main differentiator here.

## Ground truth set

- Collect 20-30 real syllabi (my own courses + classmates who opt in)
- Strip any personally identifying info before committing to the repo
- Hand-label each one into the `ExtractedSyllabus` schema (backend/app/models/schemas.py)
  - Store as JSON fixtures in `backend/app/eval/fixtures/`
- Deliberately include messy cases: scanned/image PDFs, tables as images,
  inconsistent date formats, syllabi with no explicit weight column

## Metrics

Per field type:

| Field | Metric |
|---|---|
| Assignment names | Exact match + fuzzy match (Levenshtein) rate |
| Assignment weights | % within 0.5pp of ground truth |
| Due dates | Exact date match rate |
| Assignment type classification | F1 per class (exam/homework/project/...) |
| Overall | % of syllabi with zero fields flagged incorrectly |

## Process

1. Run `backend/app/eval/run_eval.py` against the fixture set
2. Compare predicted `ExtractedSyllabus` to ground truth field-by-field
3. Log per-field accuracy to `backend/app/eval/results/` (timestamped)
4. Track accuracy over time as the pipeline changes — a regression here should
   block a merge, same as a failing test

## Confidence threshold tuning

The `needs_review` flag and per-field `confidence` score should be tuned so that:
- False negatives (wrong data shown as confident) are rare — this is the
  costly failure mode, since a student trusts a wrong deadline
- We accept a higher false-positive rate (flagging correct extractions for
  review) as the safer trade-off early on

This will become a precision/recall curve as more fixtures are added.

## Zero-shot classification upgrade (in progress)

The `type` field previously used pure keyword matching (`classify_type` in
`rule_based_extraction.py`) with a hardcoded 0.5 confidence — meaning
`needs_review` thresholding could never actually respond to type-confidence,
since it was a constant. `app/services/zero_shot_classifier.py` replaces
this with a real NLI-based zero-shot classifier (`facebook/bart-large-mnli`
via Hugging Face transformers), giving genuine per-assignment confidence.

**Status honestly:** this was built and integration-tested (see
`tests/test_zero_shot_classifier.py`) in a sandboxed dev environment without
network access to Hugging Face Hub. The tests prove the plumbing is
correct — label mapping, confidence pass-through, the on/off toggle — using
a stubbed pipeline, NOT real model inference. **No real accuracy number has
been measured yet.** Whether this actually beats the 60% keyword baseline
on `type_match` is still an open question.

To find out for real:

```bash
pip install -r requirements-ml.txt
SYLLABUSSYNC_USE_ZERO_SHOT=1 python -m app.eval.run_eval
```

Compare the `type_match` percentage against the baseline run
(`python -m app.eval.run_eval` with the env var unset). Record both numbers
here once measured — don't claim an improvement without the actual before/after.

Known risk worth checking for specifically: assignment names are often
short and generic ("Homework", "Project 1"), which may not give the NLI
model much signal to work with — it's plausible the zero-shot classifier
performs *worse* than keyword matching on names that are themselves already
keyword-like. That would be a legitimate, useful finding, not a failure of
the approach — it would tell us classification should use more context
(the surrounding sentence, not just the isolated name) rather than the
model choice being wrong.
