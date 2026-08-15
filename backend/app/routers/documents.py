from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models.schemas import ExtractedSyllabus
from app.services.extraction import extract_syllabus

router = APIRouter()


@router.post("/upload", response_model=ExtractedSyllabus)
async def upload_syllabus(file: UploadFile = File(...)):
    """
    Upload a syllabus PDF and run it through the extraction pipeline.

    v1: synchronous extraction, returns the result directly.
    Later: this should enqueue a background job and return a job id,
    since real extraction (parsing + model inference) won't be instant.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported right now")

    file_bytes = await file.read()
    result = extract_syllabus(file_bytes, filename=file.filename)
    return result
