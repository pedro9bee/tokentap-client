"""MongoDB event store for tokentap."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

from tokentap.config import MONGO_DB, MONGO_URI

logger = logging.getLogger(__name__)

COLLECTION = "events"


class MongoEventStore:
    """Async MongoDB store for proxy events."""

    def __init__(self, uri: str = MONGO_URI, db_name: str = MONGO_DB):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db[COLLECTION]
        self._indexes_created = False

    async def ensure_indexes(self) -> None:
        """Create indexes if not already created."""
        if self._indexes_created:
            return
        await self.collection.create_index("timestamp")
        await self.collection.create_index([("provider", 1), ("timestamp", -1)])
        await self.collection.create_index([("model", 1), ("timestamp", -1)])
        self._indexes_created = True

    async def insert_event(self, event: dict) -> None:
        """Insert an event (fire-and-forget style, logs errors)."""
        try:
            await self.ensure_indexes()
            if "timestamp" in event and isinstance(event["timestamp"], str):
                event["timestamp"] = datetime.fromisoformat(event["timestamp"])
            await self.collection.insert_one(event)
        except Exception:
            logger.exception("Failed to insert event into MongoDB")

    async def query_events(
        self,
        filters: dict | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        """Query events with filters and pagination. Returns (events, total_count)."""
        query = self._build_query(filters)
        total = await self.collection.count_documents(query)
        cursor = (
            self.collection.find(query)
            .sort("timestamp", -1)
            .skip(skip)
            .limit(limit)
        )
        events = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            if isinstance(doc.get("timestamp"), datetime):
                doc["timestamp"] = doc["timestamp"].isoformat()
            events.append(doc)
        return events, total

    async def get_event(self, event_id: str) -> dict | None:
        """Get a single event by ID."""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(event_id)})
        except Exception:
            return None
        if doc:
            doc["_id"] = str(doc["_id"])
            if isinstance(doc.get("timestamp"), datetime):
                doc["timestamp"] = doc["timestamp"].isoformat()
        return doc

    async def aggregate_usage(self, filters: dict | None = None) -> dict:
        """Aggregate total token usage."""
        query = self._build_query(filters)
        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "total_input_tokens": {"$sum": "$input_tokens"},
                    "total_output_tokens": {"$sum": "$output_tokens"},
                    "total_cache_creation_tokens": {"$sum": "$cache_creation_tokens"},
                    "total_cache_read_tokens": {"$sum": "$cache_read_tokens"},
                    "request_count": {"$sum": 1},
                }
            },
        ]
        result = await self.collection.aggregate(pipeline).to_list(1)
        if result:
            r = result[0]
            r.pop("_id", None)
            return r
        return {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cache_creation_tokens": 0,
            "total_cache_read_tokens": 0,
            "request_count": 0,
        }

    async def usage_by_model(self, filters: dict | None = None) -> list[dict]:
        """Token usage breakdown by provider and model."""
        query = self._build_query(filters)
        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": {"provider": "$provider", "model": "$model"},
                    "input_tokens": {"$sum": "$input_tokens"},
                    "output_tokens": {"$sum": "$output_tokens"},
                    "cache_creation_tokens": {"$sum": "$cache_creation_tokens"},
                    "cache_read_tokens": {"$sum": "$cache_read_tokens"},
                    "request_count": {"$sum": 1},
                }
            },
            {"$sort": {"input_tokens": -1}},
        ]
        results = []
        async for doc in self.collection.aggregate(pipeline):
            results.append({
                "provider": doc["_id"]["provider"],
                "model": doc["_id"]["model"],
                "input_tokens": doc["input_tokens"],
                "output_tokens": doc["output_tokens"],
                "cache_creation_tokens": doc["cache_creation_tokens"],
                "cache_read_tokens": doc["cache_read_tokens"],
                "request_count": doc["request_count"],
            })
        return results

    async def usage_over_time(
        self,
        filters: dict | None = None,
        granularity: str = "hour",
    ) -> list[dict]:
        """Token usage time series grouped by granularity (hour/day/week)."""
        query = self._build_query(filters)
        date_trunc = self._date_trunc_expr(granularity)
        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": date_trunc,
                    "input_tokens": {"$sum": "$input_tokens"},
                    "output_tokens": {"$sum": "$output_tokens"},
                    "request_count": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        results = []
        async for doc in self.collection.aggregate(pipeline):
            bucket = doc["_id"]
            if isinstance(bucket, datetime):
                bucket = bucket.isoformat()
            results.append({
                "bucket": bucket,
                "input_tokens": doc["input_tokens"],
                "output_tokens": doc["output_tokens"],
                "request_count": doc["request_count"],
            })
        return results

    async def delete_all_events(self) -> int:
        """Delete all events. Returns count of deleted documents."""
        try:
            result = await self.collection.delete_many({})
            return result.deleted_count
        except Exception:
            logger.exception("Failed to delete all events")
            return 0

    async def health_check(self) -> bool:
        """Check if MongoDB is reachable."""
        try:
            await self.client.admin.command("ping")
            return True
        except Exception:
            return False

    def _build_query(self, filters: dict | None) -> dict:
        """Build a MongoDB query from filter parameters."""
        if not filters:
            return {}
        query: dict[str, Any] = {}
        if "provider" in filters:
            query["provider"] = filters["provider"]
        if "model" in filters:
            query["model"] = filters["model"]
        if "date_from" in filters or "date_to" in filters:
            ts_query: dict[str, Any] = {}
            if "date_from" in filters:
                ts_query["$gte"] = datetime.fromisoformat(filters["date_from"])
            if "date_to" in filters:
                ts_query["$lte"] = datetime.fromisoformat(filters["date_to"])
            if ts_query:
                query["timestamp"] = ts_query
        return query

    def _date_trunc_expr(self, granularity: str) -> dict:
        """Return a $dateTrunc expression for the given granularity."""
        unit_map = {"hour": "hour", "day": "day", "week": "week"}
        unit = unit_map.get(granularity, "hour")
        return {"$dateTrunc": {"date": "$timestamp", "unit": unit}}
