"""FastAPI web dashboard API."""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tokentap.db import MongoEventStore

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Tokentap Dashboard", version="0.2.0")
db = MongoEventStore()

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


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
async def delete_all_events():
    """Delete all events from the database."""
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


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))
