from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models.db_models import Course, Assignment
from app.models.schemas import (
    CourseOut,
    CourseSummary,
    CourseUpdate,
    AssignmentUpdate,
    AssignmentOut,
    UpcomingAssignment,
)

router = APIRouter()


@router.get("/upcoming", response_model=list[UpcomingAssignment])
def list_upcoming_assignments(db: Session = Depends(get_db)):
    """
    Every assignment across every course that has a due date, sorted
    soonest-first. This is the cross-course "what's coming up" view — the
    original product pitch's "unified calendar across all your classes,"
    which until now only existed per-course, not as a single combined list.

    Deliberately placed above /{course_id} in route registration order:
    FastAPI matches routes in the order they're added, and "/upcoming"
    would otherwise be swallowed by the "/{course_id}" path parameter
    (which would try to parse "upcoming" as a UUID and 422 instead of
    reaching this handler). Route ordering here is load-bearing, not
    stylistic — moving this below /{course_id} would silently break it.
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


@router.get("/", response_model=list[CourseSummary])
def list_courses(db: Session = Depends(get_db)):
    courses = db.query(Course).options(joinedload(Course.assignments)).all()
    return [
        CourseSummary(
            id=str(c.id),
            course_code=c.course_code,
            course_name=c.course_name,
            term=c.term,
            needs_review=c.needs_review,
            total_weight_pct=sum(a.weight_pct or 0 for a in c.assignments),
        )
        for c in courses
    ]


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
