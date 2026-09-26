import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.shared.models import OptimizeRequest, OptimizeResponse
from backend.routers.rtl.engine import analyze_and_optimize_code, manager

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "online", "service": "SiliconBob Universal Code & RTL Engine"}


@router.post("/api/optimize-code", response_model=OptimizeResponse)
@router.post("/api/optimize-rtl", response_model=OptimizeResponse)
async def optimize_code_endpoint(req: OptimizeRequest):
    source_code = req.get_source_code()
    issues, optimized_code, metrics = analyze_and_optimize_code(
        code=source_code,
        language=req.language or "verilog",
        target=req.target or "ppa"
    )
    return OptimizeResponse(
        status="success",
        issues=issues,
        optimized_code=optimized_code,
        metrics=metrics
    )


@router.websocket("/ws/{room_id}")
async def websocket_collaboration(websocket: WebSocket, room_id: str):
    await manager.connect(room_id, websocket)
    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            await manager.broadcast_to_room(room_id, data, sender=websocket)
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
