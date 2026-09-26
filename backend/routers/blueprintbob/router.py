"""FastAPI Router for BlueprintBob Architecture Engine."""
from fastapi import APIRouter
from backend.shared.models import BlueprintBobRequest, BlueprintBobResponse
from backend.routers.blueprintbob.generator import generate_diagram

router = APIRouter(prefix="/api/blueprintbob", tags=["BlueprintBob"])


@router.get("/health")
def health_check():
    """Health check endpoint for BlueprintBob engine."""
    return {"status": "online", "service": "BlueprintBob Architecture Engine"}


@router.post("/generate", response_model=BlueprintBobResponse)
def generate_endpoint(request: BlueprintBobRequest):
    """Generate interactive Mermaid diagram and architectural breakdown."""
    return generate_diagram(request)
