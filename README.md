# SyllabusSync

An AI agent that turns messy course syllabi into a queryable, proactive academic assistant.

## Problem

Every course syllabus has different formatting, deadline conventions, and grading
policies. Students juggle several of these per term and miss deadlines buried in
dense text, or can't quickly answer things like "what grade do I need on the
final to get a B?"

## What it does (v1 scope)

1. Upload a syllabus (PDF) for a course
2. Extraction pipeline pulls out structured data: assignments, weights, due dates,
   grading policy, late-work rules
3. Human-in-the-loop correction UI for low-confidence extractions
4. Unified dashboard across all uploaded courses
5. Grade "what-if" simulator using extracted weights

Later phases: RAG-grounded chat over the syllabus, proactive deadline-collision
alerts, calendar export.

## Stack

- Backend: Python, FastAPI, Postgres + pgvector
- Extraction: layout-aware PDF parsing + HF models (Document QA, Table QA,
  Zero-Shot Classification, NER)
- Frontend: React (Vite)
- Infra: Docker Compose for local dev

## Repo layout

```
backend/
  app/
    routers/      # FastAPI route handlers
    models/       # Pydantic + DB models
    services/     # extraction pipeline, parsing, LLM calls
    eval/         # accuracy/F1 harness against labeled syllabi
frontend/          # Vite + React app
docs/
  eval-plan.md     # how we measure extraction accuracy
```

## Getting started

```bash
cp .env.example .env
docker compose up --build
```

Backend: http://localhost:8000/docs
Frontend: http://localhost:5173

## Status

🚧 Early scaffold. Building the extraction pipeline first — it's the highest-risk,
most differentiating piece of the project.
# syllabussync
