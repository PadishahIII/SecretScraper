"""Domain-aware rate limiter for SecretScraper.

Prevents overwhelming target servers with concurrent requests by enforcing
per-domain concurrency limits and minimum request intervals.

Usage:
    limiter = DomainRateLimiter(max_concurrent_per_domain=5, min_interval=0.5)

    async with limiter.acquire(url):
        response = await client.get(url)
"""

import asyncio
import time
from urllib.parse import urlparse
from contextlib import asynccontextmanager

__all__ = ["DomainRateLimiter"]


class DomainRateLimiter:
    """Enforce crawl etiquette with per-domain concurrency and delay.

    :param max_concurrent_per_domain: Maximum simultaneous requests to one domain.
    :param min_interval: Minimum seconds between consecutive requests to the same domain.
    """

    def __init__(
        self,
        max_concurrent_per_domain: int = 5,
        min_interval: float = 0.2,
    ):
        self._max_concurrent = max_concurrent_per_domain
        self._min_interval = min_interval
        # domain -> (semaphore, last_request_timestamp)
        self._domain_state: dict[str, tuple[asyncio.Semaphore, float]] = {}

    def _get_domain(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc or parsed.hostname or url

    def _ensure_domain(self, domain: str) -> tuple[asyncio.Semaphore, float]:
        if domain not in self._domain_state:
            self._domain_state[domain] = (
                asyncio.Semaphore(self._max_concurrent),
                0.0,
            )
        return self._domain_state[domain]

    @asynccontextmanager
    async def acquire(self, url: str):
        """Async context manager that rate-limits requests per domain."""
        domain = self._get_domain(url)
        sem, _ = self._ensure_domain(domain)

        async with sem:
            _, last_ts = self._domain_state[domain]
            now = time.monotonic()
            wait = self._min_interval - (now - last_ts)
            if wait > 0:
                await asyncio.sleep(wait)
            self._domain_state[domain] = (sem, time.monotonic())
            yield
