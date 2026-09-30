from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

logger = logging.getLogger("vaynex.health")
router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe (PostgreSQL, PostGIS, Redis)")
async def ready(request: Request) -> JSONResponse:
    checks: dict[str, dict[str, object]] = {}
    database = request.app.state.database
    try:
        async with database.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            checks["postgres"] = {"status": "ok"}
            try:
                version = await conn.scalar(text("SELECT extversion FROM pg_extension WHERE extname = 'postgis'"))
            except Exception:  # pragma: no cover - defensive
                version = None
            checks["postgis"] = {"status": "ok" if version else "unavailable", "version": version}
    except Exception as exc:
        logger.warning("Readiness: PostgreSQL unavailable (%s)", type(exc).__name__)
        checks["postgres"] = {"status": "error", "detail": type(exc).__name__}
        checks["postgis"] = {"status": "unknown"}

    redis_ok = await request.app.state.cache.ping()
    checks["redis"] = {"status": "ok" if redis_ok else "error"}

    ready_ = checks["postgres"]["status"] == "ok" and redis_ok
    status_label = "ready" if ready_ else ("degraded" if checks["postgres"]["status"] == "ok" else "not_ready")
    # Redis is a cache: without it the API still works, so readiness is 200 + "degraded".
    code = 200 if checks["postgres"]["status"] == "ok" else 503
    return JSONResponse(status_code=code, content={"status": status_label, "checks": checks})
