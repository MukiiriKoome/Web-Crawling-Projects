"""
Resilient HTTP Client with Connection Pooling and Exponential Backoff.

Demonstrates:
- Requests Session for TCP connection reuse (Keep-Alive).
- Urllib3 Retry adapter for automated handling of transient network errors & HTTP 429/5xx.
- Browser-like HTTP request headers to avoid naive bot fingerprinting.
- Timeout enforcement and clear error reporting.
"""

import logging
from typing import Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

logger = logging.getLogger(__name__)


class ResilientHttpClient:
    """
    A robust HTTP client engineered for web scraping.
    """

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (EducationalScraper/1.0)"
    )

    def __init__(
        self,
        user_agent: Optional[str] = None,
        timeout: float = 12.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        self.timeout = timeout
        self.session = requests.Session()

        # Define exponential backoff retry strategy for transient errors
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Set default headers matching real browser requests
        self.session.headers.update({
            "User-Agent": user_agent or self.DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
        })

    def fetch(self, url: str) -> Tuple[Optional[str], int, Optional[str]]:
        """
        Fetches an HTML document from the target URL.

        Returns:
            Tuple of:
            - html_text: Optional[str] (None if request failed)
            - status_code: int (0 if request failed before network response)
            - error_message: Optional[str]
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                # Ensure correct encoding (detect from headers or meta charset)
                response.encoding = response.encoding or "utf-8"
                return response.text, response.status_code, None
            else:
                return (
                    None,
                    response.status_code,
                    f"HTTP {response.status_code}: {response.reason}",
                )
        except requests.exceptions.Timeout:
            return None, 0, f"Request timed out after {self.timeout}s"
        except requests.exceptions.SSLError as e:
            return None, 0, f"SSL verification failure: {str(e)}"
        except requests.exceptions.RequestException as e:
            return None, 0, f"Network error: {str(e)}"

    def close(self):
        """Closes the underlying requests session."""
        self.session.close()
