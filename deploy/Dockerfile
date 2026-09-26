# =============================================================================
# ByteSized Backend — Multi-Stage Dockerfile
# =============================================================================
# Stage 1 (base):       Install OS deps + Python
# Stage 2 (builder):    Install Python packages into /install
# Stage 3 (production): Copy /install into a slim final image
# =============================================================================

ARG PYTHON_VERSION=3.11

# ---------------------------------------------------------------------------
# Stage 1: base — OS dependencies
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Non-root user for security
RUN groupadd --gid 1001 appgroup && \
    useradd  --uid 1001 --gid appgroup --shell /bin/sh --create-home appuser

WORKDIR /app

# ---------------------------------------------------------------------------
# Stage 2: builder — install Python dependencies
# ---------------------------------------------------------------------------
FROM base AS builder

COPY backend/requirements.txt /tmp/requirements.txt

RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r /tmp/requirements.txt

# ---------------------------------------------------------------------------
# Stage 3: production — minimal final image
# ---------------------------------------------------------------------------
FROM base AS production

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=appuser:appgroup backend/ ./backend/
COPY --chown=appuser:appgroup backend/__init__.py ./ 2>/dev/null || true

# Ensure the app can write to /tmp
RUN mkdir -p /tmp && chown appuser:appgroup /tmp

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=10s --start-period=20s --retries=4 \
    CMD curl -sf http://localhost:8000/health || exit 1

CMD ["uvicorn", "backend.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "4", "--log-level", "info", \
     "--proxy-headers", "--forwarded-allow-ips=*"]
