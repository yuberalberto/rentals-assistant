import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
]

_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


async def _request_with_retry(
    request_fn: Callable[..., Awaitable[httpx.Response]],
    method: str,
    url: str,
    max_retries: int,
    backoff_base: float,
    **kwargs: Any,
) -> httpx.Response:
    for attempt in range(max_retries + 1):
        try:
            response = await request_fn(method, url, **kwargs)
        except (httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            if attempt < max_retries:
                delay = backoff_base * (2 ** attempt) + random.random()
                logger.warning(
                    "%s on %s, retrying in %.1fs (attempt %d/%d)",
                    type(exc).__name__,
                    url,
                    delay,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(delay)
                continue
            raise

        if response.status_code in {403, 404}:
            logger.warning(
                "HTTP %s on %s — not retrying",
                response.status_code,
                url,
            )
            response.raise_for_status()

        if response.status_code in _RETRY_STATUS_CODES:
            if attempt < max_retries:
                delay = backoff_base * (2 ** attempt) + random.random()
                logger.warning(
                    "HTTP %s on %s, retrying in %.1fs (attempt %d/%d)",
                    response.status_code,
                    url,
                    delay,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(delay)
                continue
            raise httpx.HTTPStatusError(
                f"Max retries exceeded: {response.status_code}",
                request=response.request,
                response=response,
            )

        return response

    raise RuntimeError("Unexpected end of retry loop")


class _ResilientClient(httpx.AsyncClient):
    """httpx.AsyncClient that transparently retries transient errors."""

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        max_retries: int = getattr(self, "_max_retries", 3)
        backoff_base: float = getattr(self, "_backoff_base", 1.0)
        return await _request_with_retry(
            super().request, method, url, max_retries, backoff_base, **kwargs
        )


def create_client(
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
    max_retries: int = 3,
    backoff_base: float = 1.0,
    **client_kwargs: Any,
) -> httpx.AsyncClient:
    merged_headers: dict[str, str] = {
        "User-Agent": random.choice(_USER_AGENTS),
    }
    if headers:
        merged_headers.update(headers)

    client = _ResilientClient(
        headers=merged_headers,
        timeout=timeout,
        follow_redirects=True,
        **client_kwargs,
    )
    client._max_retries = max_retries  # type: ignore[attr-defined]
    client._backoff_base = backoff_base  # type: ignore[attr-defined]
    return client


async def fetch_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: Any,
) -> httpx.Response:
    if isinstance(client, _ResilientClient):
        return await client.request(method, url, **kwargs)

    max_retries: int = getattr(client, "_max_retries", 3)
    backoff_base: float = getattr(client, "_backoff_base", 1.0)
    return await _request_with_retry(
        client.request, method, url, max_retries, backoff_base, **kwargs
    )


async def fetch_with_delay(
    client: httpx.AsyncClient,
    url: str,
    *,
    min_delay: float = 1.0,
    max_delay: float = 3.0,
    method: str = "GET",
    **kwargs: Any,
) -> httpx.Response:
    delay = random.uniform(min_delay, max_delay)
    await asyncio.sleep(delay)
    if isinstance(client, _ResilientClient):
        return await fetch_with_retry(client, method, url, **kwargs)
    # DI path: use client.request() directly (compatible with test mocks)
    return await client.request(method, url, **kwargs)
