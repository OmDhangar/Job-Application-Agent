"""
src/queues/publisher.py  —  RabbitMQ async publisher.
src/queues/consumer.py   —  Generic consumer base.
"""
from __future__ import annotations

import json
import logging
from typing import Callable, Awaitable

import aio_pika

logger = logging.getLogger(__name__)


# ─── Publisher ────────────────────────────────────────────────────────────────

class QueuePublisher:
    def __init__(self, connection: aio_pika.abc.AbstractConnection) -> None:
        self._conn = connection
        self._channel: aio_pika.abc.AbstractChannel | None = None

    async def _ch(self) -> aio_pika.abc.AbstractChannel:
        if not self._channel or self._channel.is_closed:
            self._channel = await self._conn.channel()
        return self._channel

    async def publish(self, routing_key: str, payload: dict) -> None:
        ch = await self._ch()
        await ch.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=routing_key,
        )
        logger.debug("Published → %s: %s", routing_key, payload)

    @classmethod
    async def connect(cls, url: str) -> "QueuePublisher":
        conn = await aio_pika.connect_robust(url)
        return cls(conn)

