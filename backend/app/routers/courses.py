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
)

router = APIRouter()


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
    """
    Correct course-level fields (code, name, instructor, term) — the
    header info extraction often misses, unlike assignments which have
    their own dedicated correction endpoint below.
    """
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
    """
    Human-in-the-loop correction: lets a user fix a wrong extraction.
    Marks the assignment as human_corrected so we can later measure how
    often extraction actually needed fixing — a real-world accuracy
    signal beyond the eval fixture set.
    """
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
