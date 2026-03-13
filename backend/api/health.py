from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_settings()

    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    redis_ok = False
    try:
        await request.app.state.redis.ping()
        redis_ok = True
    except Exception:
        pass

    return {
        "status": "healthy" if (db_ok and redis_ok) else "degraded",
        "city": settings.city_name,
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "error",
        },
    }


@router.get("/")
async def root():
    settings = get_settings()
    return {
        "city": settings.city_name,
        "description": "Self-Governing Agent City/State",
        "api_docs": "/docs",
        "version": "0.1.0",
    }
