from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models.db_models import Course, Assignment
from app.models.schemas import (
    CourseOut,
    CourseSummary,
    CourseUpdate,
    AssignmentUpdate,
    AssignmentCreate,
    AssignmentScoreUpdate,
    AssignmentOut,
    UpcomingAssignment,
)

from app.services.extraction import REVIEW_THRESHOLD

router = APIRouter()


@router.get("/calendar.ics")
def export_calendar(db: Session = Depends(get_db)):
    """
    Exports every assignment with a due date, across every course, as a
    downloadable .ics file — importable into Google Calendar, Apple
    Calendar, Outlook, etc.

    Route ordering: must be registered before /{course_id}, or
    "/calendar.ics" would get swallowed by that path parameter and fail
    UUID validation with a 422 instead of reaching this handler.
    """
    from icalendar import Calendar, Event
    from datetime import datetime, timezone

    assignments = (
        db.query(Assignment)
        .join(Course)
        .filter(Assignment.due_date.isnot(None))
        .options(joinedload(Assignment.course))
        .all()
    )

    cal = Calendar()
    cal.add("prodid", "-//SyllabusSync//syllabussync//")
    cal.add("version", "2.0")

    for a in assignments:
        event = Event()
        course_label = a.course.course_code or "Untitled course"
        event.add("summary", f"{course_label}: {a.name}")
        event.add("dtstart", a.due_date)
        event.add("dtend", a.due_date)
        event.add("dtstamp", datetime.now(timezone.utc))
        event.add("uid", f"{a.id}@syllabussync")
        description_parts = []
        if a.weight_pct is not None:
            description_parts.append(f"Worth {a.weight_pct}% of final grade")
        if a.course.course_name:
            description_parts.append(a.course.course_name)
        if description_parts:
            event.add("description", " — ".join(description_parts))
        cal.add_component(event)

    return Response(
        content=cal.to_ical(),
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=syllabussync.ics"},
    )


@router.get("/upcoming", response_model=list[UpcomingAssignment])
def list_upcoming_assignments(db: Session = Depends(get_db)):
    """
    Every assignment across every course that has a due date, sorted
    soonest-first.

    Route ordering: must be registered before /{course_id} — same concern
    as /calendar.ics above.
    """
    assignments = (
        db.query(Assignment)
        .join(Course)
        .filter(Assignment.due_date.isnot(None))
        .options(joinedload(Assignment.course))
        .order_by(Assignment.due_date.asc())
        .all()
    )

    return [
        UpcomingAssignment(
            assignment_id=str(a.id),
            course_id=str(a.course_id),
            course_code=a.course.course_code,
            course_name=a.course.course_name,
            name=a.name,
            type=a.type,
            weight_pct=a.weight_pct,
            due_date=a.due_date,
            confidence=a.confidence,
        )
        for a in assignments
    ]


def _compute_running_grade(assignments: list[Assignment]) -> tuple[float | None, float]:
    """
    Mirrors the same weighted-grade math the frontend's GradeSimulator has
    always done client-side. Returns (current_grade_pct, graded_weight_pct);
    current_grade_pct is None (not 0) when nothing has a score yet.
    """
    scored = [a for a in assignments if a.score_pct is not None and a.weight_pct is not None]
    if not scored:
        return None, 0.0

    current_grade_pct = sum((a.score_pct / 100) * a.weight_pct for a in scored)
    graded_weight_pct = sum(a.weight_pct for a in scored)
    return current_grade_pct, graded_weight_pct


@router.get("/", response_model=list[CourseSummary])
def list_courses(db: Session = Depends(get_db)):
    courses = db.query(Course).options(joinedload(Course.assignments)).all()
    result = []
    for c in courses:
        current_grade_pct, graded_weight_pct = _compute_running_grade(c.assignments)
        result.append(
            CourseSummary(
                id=str(c.id),
                course_code=c.course_code,
                course_name=c.course_name,
                term=c.term,
                needs_review=c.needs_review,
                total_weight_pct=sum(a.weight_pct or 0 for a in c.assignments),
                current_grade_pct=current_grade_pct,
                graded_weight_pct=graded_weight_pct,
            )
        )
    return result


@router.get("/{course_id}", response_model=CourseOut)
def get_course(course_id: UUID, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.patch("/{course_id}", response_model=CourseOut)
def update_course(course_id: UUID, update: CourseUpdate, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)

    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}", status_code=204)
def delete_course(course_id: UUID, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    db.delete(course)
    db.commit()


@router.patch("/{course_id}/assignments/{assignment_id}", response_model=AssignmentOut)
def correct_assignment(
    course_id: UUID,
    assignment_id: UUID,
    update: AssignmentUpdate,
    db: Session = Depends(get_db),
):
    assignment = (
        db.query(Assignment)
        .filter(Assignment.id == assignment_id, Assignment.course_id == course_id)
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "type" and value is not None:
            value = value.value
        setattr(assignment, field, value)

    if update_data:
        assignment.human_corrected = True

    db.commit()
    db.refresh(assignment)
    return assignment


@router.patch("/{course_id}/assignments/{assignment_id}/score", response_model=AssignmentOut)
def record_assignment_score(
    course_id: UUID,
    assignment_id: UUID,
    update: AssignmentScoreUpdate,
    db: Session = Depends(get_db),
):
    """
    Records the actual score received — separate from correct_assignment
    above, which fixes wrong extraction fields. Doesn't touch
    human_corrected or confidence.
    """
    assignment = (
        db.query(Assignment)
        .filter(Assignment.id == assignment_id, Assignment.course_id == course_id)
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    assignment.score_pct = update.score_pct
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/{course_id}/assignments", response_model=AssignmentOut, status_code=201)
def create_assignment(course_id: UUID, new_assignment: AssignmentCreate, db: Session = Depends(get_db)):
    """
    Manually add an assignment a human typed in directly — closes the gap
    where, if extraction found zero assignments, there was no way to add
    one at all.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    assignment = Assignment(
        course_id=course.id,
        name=new_assignment.name,
        type=new_assignment.type.value,
        weight_pct=new_assignment.weight_pct,
        due_date=new_assignment.due_date,
        raw_source_text="Added manually",
        confidence=1.0,
        human_corrected=True,
    )
    db.add(assignment)
    db.flush()

    course.needs_review = any(a.confidence < REVIEW_THRESHOLD for a in course.assignments)

    db.commit()
    db.refresh(assignment)
    return assignment
