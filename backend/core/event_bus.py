import json
import asyncio
import logging
from typing import Callable, Awaitable

import redis.asyncio as aioredis

from backend.config import get_settings

logger = logging.getLogger(__name__)


class EventBus:
    """Redis-backed pub/sub event bus for city-wide events."""

    CHANNEL = "city_events"

    def __init__(self, redis_client: aioredis.Redis):
        self._redis = redis_client
        self._handlers: dict[str, list[Callable]] = {}
        self._pubsub: aioredis.client.PubSub | None = None

    async def publish(self, event_type: str, data: dict):
        message = json.dumps({"type": event_type, **data})
        await self._redis.publish(self.CHANNEL, message)
        logger.debug("Published event: %s", event_type)

    def subscribe(self, event_type: str, handler: Callable[[dict], Awaitable[None]]):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def start_listening(self):
        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe(self.CHANNEL)
        logger.info("EventBus listening on channel: %s", self.CHANNEL)

        async for message in self._pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
                event_type = data.get("type", "")
                handlers = self._handlers.get(event_type, [])
                for handler in handlers:
                    try:
                        await handler(data)
                    except Exception:
                        logger.exception("Error in event handler for %s", event_type)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON on event bus")

    async def stop(self):
        if self._pubsub:
            await self._pubsub.unsubscribe(self.CHANNEL)
            await self._pubsub.close()


_event_bus: EventBus | None = None


async def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        settings = get_settings()
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        _event_bus = EventBus(redis_client)
    return _event_bus
