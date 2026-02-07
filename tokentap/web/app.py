"""FastAPI web dashboard API."""

from pathlib import Path
from typing import Optional
import logging
from functools import wraps

from fastapi import FastAPI, HTTPException, Query, Request, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tokentap.db import MongoEventStore
from tokentap.config import get_or_create_admin_token

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Tokentap Dashboard", version="0.6.0")
db = MongoEventStore()

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# NEW v0.6.0: Admin token authentication for destructive operations
def verify_admin_token(x_admin_token: Optional[str] = Header(None)):
    """Verify admin token for destructive operations."""
    if not x_admin_token:
        raise HTTPException(
            status_code=403,
            detail="Admin token required. Get token with: tokentap admin-token"
        )

    expected_token = get_or_create_admin_token()
    if x_admin_token != expected_token:
        raise HTTPException(
            status_code=403,
            detail="Invalid admin token"
        )
    return True


@app.get("/api/health")
async def health():
    mongo_ok = await db.health_check()
    return {"status": "ok", "mongodb": mongo_ok}


@app.get("/api/events")
async def list_events(
    provider: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    filters = {}
    if provider:
        filters["provider"] = provider
    if model:
        filters["model"] = model
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to

    events, total = await db.query_events(filters=filters, skip=skip, limit=limit)
    return {"events": events, "total": total, "skip": skip, "limit": limit}


@app.get("/api/events/{event_id}")
async def get_event(event_id: str):
    event = await db.get_event(event_id)
    if not event:
        return {"error": "Event not found"}, 404
    return event


@app.delete("/api/events/all")
async def delete_all_events(authenticated: bool = Header(default=None, alias="X-Admin-Token")):
    """Delete all events from the database. Requires admin token."""
    verify_admin_token(authenticated)
    deleted_count = await db.delete_all_events()
    return {"deleted_count": deleted_count, "status": "ok"}


@app.get("/api/stats/summary")
async def stats_summary(
    provider: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    filters = {}
    if provider:
        filters["provider"] = provider
    if model:
        filters["model"] = model
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    return await db.aggregate_usage(filters)


@app.get("/api/stats/by-model")
async def stats_by_model(
    provider: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    filters = {}
    if provider:
        filters["provider"] = provider
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    return await db.usage_by_model(filters)


@app.get("/api/stats/by-program")
async def stats_by_program(
    provider: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Get token usage aggregated by program (NEW in v0.6.0)."""
    filters = {}
    if provider:
        filters["provider"] = provider
    if model:
        filters["model"] = model
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    return await db.usage_by_program(filters)


@app.get("/api/stats/by-project")
async def stats_by_project(
    provider: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Get token usage aggregated by project (NEW in v0.6.0)."""
    filters = {}
    if provider:
        filters["provider"] = provider
    if model:
        filters["model"] = model
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    return await db.usage_by_project(filters)


@app.get("/api/stats/over-time")
async def stats_over_time(
    granularity: str = Query("hour", pattern="^(hour|day|week)$"),
    provider: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    filters = {}
    if provider:
        filters["provider"] = provider
    if model:
        filters["model"] = model
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    return await db.usage_over_time(filters=filters, granularity=granularity)


# -------------------------------------------------------------------------
# NEW v0.5.0: Device management endpoints
# -------------------------------------------------------------------------

@app.get("/api/devices")
async def list_devices():
    """List all devices with their stats and custom names."""
    try:
        devices = await db.get_devices()
        return devices
    except Exception as e:
        logger.exception("Failed to get devices")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/devices/{device_id}/rename")
async def rename_device(device_id: str, request: Request):
    """Rename a device with custom name."""
    try:
        body = await request.json()
        name = body.get("name", "").strip()

        if not name:
            raise HTTPException(status_code=400, detail="Name cannot be empty")

        await db.register_device(device_id, name)
        return {"status": "ok", "device_id": device_id, "name": name}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to rename device")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: str, authenticated: bool = Header(default=None, alias="X-Admin-Token")):
    """Delete device registration (historical events are kept). Requires admin token."""
    verify_admin_token(authenticated)
    try:
        await db.delete_device(device_id)
        return {"status": "ok", "device_id": device_id}
    except Exception as e:
        logger.exception("Failed to delete device")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats/by-device")
async def stats_by_device(
    provider: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Get token usage aggregated by device."""
    try:
        filters = {}
        if provider:
            filters["provider"] = provider
        if model:
            filters["model"] = model
        if date_from:
            filters["date_from"] = date_from
        if date_to:
            filters["date_to"] = date_to

        return await db.usage_by_device(filters)
    except Exception as e:
        logger.exception("Failed to get device stats")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))
