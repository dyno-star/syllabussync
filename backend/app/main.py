from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, engine
from app.routers import courses, documents
from app.models import db_models  # noqa: F401 — import registers models with Base

app = FastAPI(title="SyllabusSync API", version="0.1.0")

# v1: create tables directly on startup. Fine for a single-developer
# portfolio project; a real production app would use Alembic migrations
# instead so schema changes are tracked and reversible.
Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(courses.router, prefix="/api/courses", tags=["courses"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])


@app.get("/health")
def health():
    return {"status": "ok"}
