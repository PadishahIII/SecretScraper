import asyncio
import time

import pytest

from secretscraper.rate_limiter import DomainRateLimiter


@pytest.mark.asyncio
async def test_domain_rate_limiter_enforces_per_domain_concurrency():
    limiter = DomainRateLimiter(max_concurrent_per_domain=1, min_interval=0)
    active = 0
    max_active = 0

    async def worker():
        nonlocal active, max_active
        async with limiter.acquire("http://example.com/test"):
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.02)
            active -= 1

    await asyncio.gather(*(worker() for _ in range(3)))

    assert max_active == 1


@pytest.mark.asyncio
async def test_domain_rate_limiter_enforces_min_interval():
    limiter = DomainRateLimiter(max_concurrent_per_domain=5, min_interval=0.05)
    timestamps = []

    async with limiter.acquire("http://example.com/one"):
        timestamps.append(time.monotonic())

    async with limiter.acquire("http://example.com/two"):
        timestamps.append(time.monotonic())

    assert timestamps[1] - timestamps[0] >= 0.045
