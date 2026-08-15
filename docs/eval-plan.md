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
