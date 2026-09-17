from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.db_models import Course, Assignment
from app.models.schemas import CourseOut
from app.services.extraction import extract_syllabus

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.wordprocessingml.template",  # .dotx
}


@router.post("/upload", response_model=CourseOut)
async def upload_syllabus(file: UploadFile = File(...), db: Session = Depends(get_db)):
    lower_name = file.filename.lower()
    matches_extension = lower_name.endswith(".docx") or lower_name.endswith(".dotx")
    if file.content_type not in ALLOWED_CONTENT_TYPES and not matches_extension:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, .docx, and .dotx uploads are supported right now",
        )

    file_bytes = await file.read()
    extracted = extract_syllabus(file_bytes, filename=file.filename, content_type=file.content_type)

    course = Course(
        course_code=extracted.course_code,
        course_name=extracted.course_name,
        instructor=extracted.instructor,
        term=extracted.term,
        source_filename=file.filename,
        needs_review=extracted.needs_review,
    )
    db.add(course)
    db.flush()

    for a in extracted.assignments:
        db.add(
            Assignment(
                course_id=course.id,
                name=a.name,
                type=a.type.value,
                weight_pct=a.weight_pct,
                due_date=a.due_date,
                raw_source_text=a.raw_source_text,
                confidence=a.confidence,
            )
        )

    db.commit()
    db.refresh(course)
    return course
