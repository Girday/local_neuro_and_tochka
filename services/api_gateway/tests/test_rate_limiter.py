import asyncio

import pytest
from fastapi import HTTPException

from api_gateway.core.rate_limit import RateLimiter


async def _consume(limiter: RateLimiter, key: str, times: int) -> None:
    for _ in range(times):
        await limiter.check(key)


def test_rate_limiter_blocks_after_limit() -> None:
    limiter = RateLimiter(limit_per_minute=2)

    async def scenario() -> None:
        await _consume(limiter, "tenant:user", times=2)
        with pytest.raises(HTTPException) as exc_info:
            await limiter.check("tenant:user")
        assert exc_info.value.status_code == 429

    asyncio.run(scenario())


def test_rate_limiter_isolated_keys() -> None:
    limiter = RateLimiter(limit_per_minute=1)

    async def scenario() -> None:
        await limiter.check("tenant:user-a")
        # Different key should still be allowed
        await limiter.check("tenant:user-b")

    asyncio.run(scenario())
