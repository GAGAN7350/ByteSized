"""FastAPI Router for BlueprintBob Architecture Engine."""
import logging

from fastapi import APIRouter, Request
from backend.shared.models import BlueprintBobRequest, BlueprintBobResponse
from backend.routers.blueprintbob.generator import generate_diagram

logger = logging.getLogger("bytesized.blueprintbob")
router = APIRouter(prefix="/api/blueprintbob", tags=["BlueprintBob"])


@router.get("/health", tags=["ops"])
def health_check():
    """Health check endpoint for BlueprintBob engine."""
    return {"status": "online", "service": "BlueprintBob Architecture Engine"}


@router.post(
    "/generate",
    response_model=BlueprintBobResponse,
    summary="Generate Mermaid architecture diagram from a repository file tree",
)
def generate_endpoint(http_request: Request, request: BlueprintBobRequest):
    """
    Analyses a repository file tree and key file contents to produce:
    - An interactive Mermaid flowchart diagram
    - A structured graph (nodes, edges, groups)
    - An architectural explanation

    Supports two engine modes:
    - `offline` — deterministic AST-based analysis (no API key required)
    - `ai` — Gemini/OpenAI-powered analysis (requires `api_key`)
    """
    # Guard: reject path-traversal in file_tree entries
    from fastapi import HTTPException
    for path in request.file_tree:
        if ".." in path or path.startswith("/"):
            raise HTTPException(
                status_code=422,
                detail=f"file_tree entry contains unsafe path: {path!r}",
            )

    logger.debug(
        '"event":"generate","engine":"%s","files":%d',
        request.engine_mode,
        len(request.file_tree),
    )
    return generate_diagram(request)
