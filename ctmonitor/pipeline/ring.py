"""BoundedRing async queue for CT events."""

import asyncio
from typing import Generic, TypeVar, Optional

T = TypeVar("T")

class BoundedRing(Generic[T]):
    """
    Fixed-capacity async queue wrapped over an internal list.
    Automatically drops the oldest item on overflow to prevent OOM.
    Crucial for handling the 12+ certs/sec CT log firehose.
    """

    def __init__(self, capacity: int = 10000) -> None:
        self.capacity = capacity
        self._queue: asyncio.Queue[T] = asyncio.Queue(maxsize=capacity)
        self.dropped_count = 0

    async def put(self, item: T) -> None:
        """Add an item to the ring, dropping the oldest if full."""
        try:
            self._queue.put_nowait(item)
        except asyncio.QueueFull:
            # Queue is full, pop the oldest and try again
            try:
                self._queue.get_nowait()
                self.dropped_count += 1
            except asyncio.QueueEmpty:
                pass
            
            # Put the new item
            await self._queue.put(item)

    async def get(self) -> T:
        """Get an item from the ring. Blocks if empty."""
        return await self._queue.get()

    def qsize(self) -> int:
        """Get current size of the ring."""
        return self._queue.qsize()
