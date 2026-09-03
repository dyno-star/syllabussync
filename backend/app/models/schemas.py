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
    name: str
    type: AssignmentType
    weight_pct: float | None = Field(default=None)
    due_date: date | None = None
    raw_source_text: str = Field(default="")
    confidence: float = Field(ge=0.0, le=1.0)


class GradingPolicy(BaseModel):
    late_policy: str | None = None
    grading_scale: dict[str, str] | None = None


class ExtractedSyllabus(BaseModel):
    course_code: str | None = None
    course_name: str | None = None
    instructor: str | None = None
    term: str | None = None
    assignments: list[ExtractedAssignment] = Field(default_factory=list)
    grading_policy: GradingPolicy | None = None
    needs_review: bool = Field(default=False)


# --- Persisted / API-facing schemas ---


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
    name: str | None = None
    type: AssignmentType | None = None
    weight_pct: float | None = None
    due_date: date | None = None


class AssignmentCreate(BaseModel):
    """
    For manually adding an assignment a human typed in directly — as
    opposed to one extraction produced. Name and type are required (there's
    no reasonable default for either); weight and due date are optional
    since a user might want to log "there's a final project" before they
    know its exact weight or date yet.
    """

    name: str = Field(min_length=1)
    type: AssignmentType
    weight_pct: float | None = None
    due_date: date | None = None


class CourseUpdate(BaseModel):
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
    id: str
    course_code: str | None
    course_name: str | None
    term: str | None
    needs_review: bool
    total_weight_pct: float

    @field_validator("id", mode="before")
    @classmethod
    def coerce_uuid(cls, v):
        return str(v)

    class Config:
        from_attributes = True


class UpcomingAssignment(BaseModel):
    """
    One assignment with its due date, flattened together with just enough
    course context to display it in a cross-course deadlines list — not
    the full CourseOut, since the deadlines view doesn't need every field
    (instructor, needs_review, etc.) and flattening avoids the frontend
    having to do its own join.
    """

    assignment_id: str
    course_id: str
    course_code: str | None
    course_name: str | None
    name: str
    type: AssignmentType
    weight_pct: float | None
    due_date: date
    confidence: float

    @field_validator("assignment_id", "course_id", mode="before")
    @classmethod
    def coerce_uuid(cls, v):
        return str(v)

    class Config:
        from_attributes = True
