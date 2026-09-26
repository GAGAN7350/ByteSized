from fastapi import APIRouter

router = APIRouter()


@router.get("/2nd-ext/health")
def health_check():
    """Health check for the 2nd-ext extension backend."""
    return {"status": "online", "service": "2nd-ext"}
