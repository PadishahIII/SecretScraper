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
from contextlib import asynccontextmanager
from dataclasses import dataclass
from urllib.parse import urlparse

__all__ = ["DomainRateLimiter"]


@dataclass
class _DomainState:
    semaphore: asyncio.Semaphore
    interval_lock: asyncio.Lock
    last_request_started: float = 0.0


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
        if max_concurrent_per_domain < 1:
            raise ValueError("max_concurrent_per_domain must be at least 1")
        if min_interval < 0:
            raise ValueError("min_interval must be non-negative")

        self.max_concurrent_per_domain = max_concurrent_per_domain
        self.min_interval = min_interval
        self._domain_state: dict[str, _DomainState] = {}
        self._state_lock = asyncio.Lock()

    def _get_domain(self, url: str) -> str:
        parsed = urlparse(url)
        return (parsed.hostname or parsed.netloc or url).lower()

    async def _get_domain_state(self, domain: str) -> _DomainState:
        async with self._state_lock:
            state = self._domain_state.get(domain)
            if state is None:
                state = _DomainState(
                    semaphore=asyncio.Semaphore(self.max_concurrent_per_domain),
                    interval_lock=asyncio.Lock(),
                )
                self._domain_state[domain] = state
            return state

    @asynccontextmanager
    async def acquire(self, url: str):
        """Async context manager that rate-limits requests per domain."""
        domain = self._get_domain(url)
        state = await self._get_domain_state(domain)

        await state.semaphore.acquire()
        try:
            async with state.interval_lock:
                wait = self.min_interval - (
                    time.monotonic() - state.last_request_started
                )
                if wait > 0:
                    await asyncio.sleep(wait)
                state.last_request_started = time.monotonic()
            yield
        finally:
            state.semaphore.release()
