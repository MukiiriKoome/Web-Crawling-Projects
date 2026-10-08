"""
High-Performance Asynchronous HTTP Client with Concurrency Limiting.

Demonstrates:
- httpx.AsyncClient for asynchronous I/O and non-blocking network calls.
- asyncio.Semaphore to enforce concurrency thresholds and avoid hammering servers.
- Asynchronous exponential backoff retries on transient errors and HTTP 429.
- Custom headers and connection pool management.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Tuple
import httpx

logger = logging.getLogger(__name__)


class AsyncHttpClient:
    """
    Asynchronous HTTP client equipped with concurrency limiting and exponential backoff.
    """

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (AsyncScraper/2.0)"
        ),
        "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(
        self,
        max_concurrency: int = 5,
        timeout: float = 12.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        limits = httpx.Limits(max_keepalive_connections=15, max_connections=25)
        self.client = httpx.AsyncClient(
            headers=self.DEFAULT_HEADERS,
            timeout=self.timeout,
            limits=limits,
            follow_redirects=True,
        )

    async def get(self, url: str) -> httpx.Response:
        """
        Executes a GET request guarded by the concurrency semaphore and retry loop.
        """
        last_exception = None

        for attempt in range(self.max_retries):
            async with self.semaphore:
                try:
                    response = await self.client.get(url)
                    # Retry on server errors or rate limiting
                    if response.status_code in [429, 500, 502, 503, 504]:
                        wait_time = self.backoff_factor * (2 ** attempt)
                        logger.warning(
                            f"HTTP {response.status_code} on {url}. Retrying in {wait_time:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    return response

                except (httpx.RequestError, httpx.HTTPStatusError) as e:
                    last_exception = e
                    wait_time = self.backoff_factor * (2 ** attempt)
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Network error on {url}: {e}. Retrying in {wait_time:.1f}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        raise e

        if last_exception:
            raise last_exception
        raise httpx.RequestError(f"Failed to fetch {url} after {self.max_retries} attempts")

    async def fetch_json(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetches and decodes a JSON payload asynchronously."""
        try:
            resp = await self.get(url)
            return resp.json()
        except Exception as e:
            logger.error(f"Error fetching JSON from {url}: {e}")
            return None

    async def fetch_html(self, url: str) -> Optional[str]:
        """Fetches raw HTML document content asynchronously."""
        try:
            resp = await self.get(url)
            return resp.text
        except Exception as e:
            logger.error(f"Error fetching HTML from {url}: {e}")
            return None

    async def aclose(self):
        """Cleanly releases TCP connections and resources."""
        await self.client.aclose()
