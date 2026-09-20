from uuid import UUID

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.db_models import Course, Assignment
from app.models.schemas import CourseOut, ExtractedSyllabus
from app.services.extraction import extract_syllabus, REVIEW_THRESHOLD

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.wordprocessingml.template",  # .dotx
}


def _validate_upload(file: UploadFile) -> None:
    lower_name = file.filename.lower()
    matches_extension = lower_name.endswith(".docx") or lower_name.endswith(".dotx")
    if file.content_type not in ALLOWED_CONTENT_TYPES and not matches_extension:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, .docx, and .dotx uploads are supported right now",
        )


@router.post("/upload", response_model=CourseOut)
async def upload_syllabus(file: UploadFile = File(...), db: Session = Depends(get_db)):
    _validate_upload(file)

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


def _merge_reupload_into_course(course: Course, extracted: ExtractedSyllabus, db: Session) -> None:
    """
    Merges freshly-extracted data from a re-uploaded (revised) syllabus
    into an EXISTING course, rather than replacing it wholesale.

    Rules, in order of what they protect:
    - score_pct (the student's actual earned grade) is NEVER touched by
      re-upload — it isn't extraction's business, and a revised syllabus
      can't possibly know what you scored on something.
    - An assignment the user has manually corrected (human_corrected=True)
      keeps its corrected values — the human's correction outranks a new
      extraction pass, on the assumption a person fixing a field knows
      better than another OCR/regex pass on a new file.
    - Course-level fields (code, name, instructor, term) only fill in
      currently-empty ones — never overwrite an existing value, since we
      can't tell whether it came from extraction or a manual correction
      (Course, unlike Assignment, has no per-field "corrected" flag).
    - An assignment in the new extraction that doesn't match any existing
      one by name is added as new — this is the common real case: a
      revised syllabus added a project, changed a due date on a named
      assignment, or both.
    - An existing assignment not found in the new extraction is left
      alone, not deleted — revised syllabi essentially never remove
      graded items, and deleting is a strictly worse failure mode than
      leaving a stale row for the user to remove by hand if truly gone.

    Matching is by exact case-insensitive name — a real, known limitation:
    if a professor renames "Midterm" to "Midterm Exam" between versions,
    this won't recognize them as the same assignment and will add a
    second row instead of updating the first. Fuzzy matching would help
    but risks the opposite failure (merging two genuinely different
    assignments that happen to have similar names), which is worse than
    an extra row a user can manually clean up.
    """
    existing_by_name = {a.name.strip().lower(): a for a in course.assignments}

    for extracted_assignment in extracted.assignments:
        key = extracted_assignment.name.strip().lower()
        existing = existing_by_name.get(key)

        if existing is None:
            db.add(
                Assignment(
                    course_id=course.id,
                    name=extracted_assignment.name,
                    type=extracted_assignment.type.value,
                    weight_pct=extracted_assignment.weight_pct,
                    due_date=extracted_assignment.due_date,
                    raw_source_text=extracted_assignment.raw_source_text,
                    confidence=extracted_assignment.confidence,
                )
            )
        elif not existing.human_corrected:
            existing.type = extracted_assignment.type.value
            existing.weight_pct = extracted_assignment.weight_pct
            existing.due_date = extracted_assignment.due_date
            existing.raw_source_text = extracted_assignment.raw_source_text
            existing.confidence = extracted_assignment.confidence
        # else: human-corrected — leave existing values entirely alone.
        # score_pct is never touched in either branch above.

    if extracted.course_code and not course.course_code:
        course.course_code = extracted.course_code
    if extracted.course_name and not course.course_name:
        course.course_name = extracted.course_name
    if extracted.instructor and not course.instructor:
        course.instructor = extracted.instructor
    if extracted.term and not course.term:
        course.term = extracted.term

    db.flush()
    course.needs_review = any(a.confidence < REVIEW_THRESHOLD for a in course.assignments)


@router.post("/reupload/{course_id}", response_model=CourseOut)
async def reupload_syllabus(
    course_id: UUID, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    """
    For when a professor issues a revised syllabus mid-term: re-runs
    extraction on the new file and merges the results into the EXISTING
    course (see _merge_reupload_into_course for the merge rules), rather
    than creating a duplicate course the way a second /upload would.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    _validate_upload(file)

    file_bytes = await file.read()
    extracted = extract_syllabus(file_bytes, filename=file.filename, content_type=file.content_type)

    course.source_filename = file.filename
    _merge_reupload_into_course(course, extracted, db)

    db.commit()
    db.refresh(course)
    return course
