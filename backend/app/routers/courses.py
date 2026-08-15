from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_courses():
    """
    Returns all courses the user has uploaded syllabi for.

    Stub for now — wire up to Postgres once the extraction pipeline
    is producing reliable output worth persisting.
    """
    return []
