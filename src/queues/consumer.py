
# ─── Consumer base ────────────────────────────────────────────────────────────
from __future__ import annotations

import json
import logging
from typing import Callable, Awaitable

import aio_pika

logger = logging.getLogger(__name__)


class QueueConsumer:
    def __init__(self, url: str, queue_name: str) -> None:
        self.url = url
        self.queue_name = queue_name

    async def run(
        self, handler: Callable[[dict], Awaitable[None]], prefetch: int = 5
    ) -> None:
        conn = await aio_pika.connect_robust(self.url)
        async with conn:
            ch = await conn.channel()
            await ch.set_qos(prefetch_count=prefetch)
            queue = await ch.declare_queue(self.queue_name, durable=True)
            logger.info("Consuming from %s", self.queue_name)
            async with queue.iterator() as it:
                async for message in it:
                    async with message.process(requeue=True):
                        try:
                            payload = json.loads(message.body)
                            await handler(payload)
                        except Exception as e:
                            logger.error("Handler error [%s]: %s", self.queue_name, e)
                            raise