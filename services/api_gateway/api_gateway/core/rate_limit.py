import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, status


class RateLimiter:
    def __init__(self, limit_per_minute: int) -> None:
        self.limit = limit_per_minute
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> None:
        async with self._lock:
            now = time.time()
            window_start = now - 60
            bucket = self._hits[key]
            while bucket and bucket[0] < window_start:
                bucket.popleft()
            if len(bucket) >= self.limit:
                retry_after = max(1, int(bucket[0] + 60 - now))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={"code": "rate_limit_exceeded", "retry_after": retry_after},
                )
            bucket.append(now)
