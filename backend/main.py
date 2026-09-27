"""
ByteSized Backend — Application factory.

Mounts all extension routers and wires up cross-cutting concerns:
  • Structured JSON logging with request-ID propagation
  • CORS restricted to configured origins (env: CORS_ORIGINS)
  • Rate limiting via slowapi (env: RATE_LIMIT_PER_MINUTE)
  • /health liveness probe (used by Docker HEALTHCHECK and load-balancers)
"""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.config import get_settings
from backend.routers.rtl.router import router as rtl_router
from backend.routers.blueprintbob.router import router as blueprintbob_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
settings = get_settings()

logging.basicConfig(
    level=settings.log_level.upper(),
    format='{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":%(message)s}',
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger("bytesized")

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ByteSized Backend API",
    description="Electronic Chip Design & RTL Optimization Engine for IBM Bob — Multi-Extension Platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# CORS — restricted to configured origins, never wildcard in production
# ---------------------------------------------------------------------------
_origins = settings.cors_origins_list
if settings.is_production and "*" in _origins:
    logger.warning('"msg":"CORS wildcard (*) detected in production — this is insecure. Set CORS_ORIGINS."')
    _origins = []  # deny all rather than allow all in production

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# ---------------------------------------------------------------------------
# Request-ID + access logging middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def request_id_and_logging(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    t0 = time.perf_counter()
    try:
        response: Response = await call_next(request)
    except Exception:
        logger.exception(
            '"request_id":"%s","path":"%s","error":"unhandled exception"',
            request_id, request.url.path,
        )
        raise

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        '"request_id":"%s","method":"%s","path":"%s","status":%d,"duration_ms":%s',
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response

# ---------------------------------------------------------------------------
# MOUNT EXTENSION ROUTERS
# Add one include_router() call per new extension below.
# ---------------------------------------------------------------------------
app.include_router(rtl_router)
app.include_router(blueprintbob_router)

# ---------------------------------------------------------------------------
# Global health / liveness endpoint
# ---------------------------------------------------------------------------
@app.get("/health", tags=["ops"], summary="Liveness probe")
def health_check():
    """
    Returns `{"status":"online"}`.
    Used by Docker HEALTHCHECK, Kubernetes liveness probes, and nginx upstream checks.
    """
    return JSONResponse(
        content={
            "status": "online",
            "service": "ByteSized Backend",
            "version": app.version,
            "environment": settings.environment,
        }
    )
