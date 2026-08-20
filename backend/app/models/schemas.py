from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class AssignmentType(str, Enum):
    exam = "exam"
    homework = "homework"
    project = "project"
    quiz = "quiz"
    participation = "participation"
    other = "other"


class ExtractedAssignment(BaseModel):
    """A single graded item pulled out of a syllabus."""

    name: str
    type: AssignmentType
    weight_pct: float | None = Field(
        default=None, description="Percent of final grade, e.g. 20.0 for 20%"
    )
    due_date: date | None = None
    raw_source_text: str = Field(
        description="The original syllabus text this was extracted from, for auditability"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Extraction confidence, used to flag for human review"
    )


class GradingPolicy(BaseModel):
    late_policy: str | None = None
    grading_scale: dict[str, str] | None = Field(
        default=None, description='e.g. {"A": "93-100", "A-": "90-92"}'
    )


class ExtractedSyllabus(BaseModel):
    course_code: str | None = None
    course_name: str | None = None
    instructor: str | None = None
    term: str | None = None
    assignments: list[ExtractedAssignment] = Field(default_factory=list)
    grading_policy: GradingPolicy | None = None
    needs_review: bool = Field(
        default=False,
        description="True if any extracted field fell below the confidence threshold",
    )


# --- Persisted / API-facing schemas (used by courses router) ---


class AssignmentOut(BaseModel):
    id: str
    name: str
    type: AssignmentType
    weight_pct: float | None
    due_date: date | None
    confidence: float
    human_corrected: bool

    @field_validator("id", mode="before")
    @classmethod
    def coerce_uuid(cls, v):
        return str(v)

    class Config:
        from_attributes = True


class AssignmentUpdate(BaseModel):
    """Fields a user can correct via the human-in-the-loop review UI."""

    name: str | None = None
    type: AssignmentType | None = None
    weight_pct: float | None = None
    due_date: date | None = None


class CourseUpdate(BaseModel):
    """Fields a user can correct on the course itself (not its assignments)."""

    course_code: str | None = None
    course_name: str | None = None
    instructor: str | None = None
    term: str | None = None


class CourseOut(BaseModel):
    id: str
    course_code: str | None
    course_name: str | None
    instructor: str | None
    term: str | None
    needs_review: bool
    created_at: datetime
    assignments: list[AssignmentOut]

    @field_validator("id", mode="before")
    @classmethod
    def coerce_uuid(cls, v):
        return str(v)

    class Config:
        from_attributes = True


class CourseSummary(BaseModel):
    """Lightweight version for the course list view — no assignments."""

    id: str
    course_code: str | None
    course_name: str | None
    term: str | None
    needs_review: bool
    total_weight_pct: float = Field(
        description="Sum of assignment weights, so the UI can flag if it doesn't add to 100"
    )

    @field_validator("id", mode="before")
    @classmethod
    def coerce_uuid(cls, v):
        return str(v)

    class Config:
        from_attributes = True
