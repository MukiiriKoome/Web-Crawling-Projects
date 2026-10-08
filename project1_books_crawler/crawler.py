"""
Crawler Orchestrator Module for Project 1.

Demonstrates:
- Coordinating Frontier, HTTP Client, Parser, and Storage in a unified event loop.
- Termination conditions (max pages, max depth, empty frontier).
- Error handling and non-crashing fault tolerance.
- Event hooks/callbacks for real-time UI logging and stats tracking.
"""

from datetime import datetime, timezone
import logging
import time
from typing import Callable, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from .frontier import UrlFrontier
from .http_client import ResilientHttpClient
from .models import BookItem, CrawlStats
from .parser import BookPageParser
from .storage import StoragePipeline

logger = logging.getLogger(__name__)


class BooksCrawler:
    """
    Polite, recursive web crawler for catalog data extraction.
    """

    def __init__(
        self,
        start_url: str = "https://books.toscrape.com/",
        max_pages: int = 15,
        max_depth: int = 2,
        delay: float = 0.5,
        respect_robots: bool = True,
        storage: Optional[StoragePipeline] = None,
        on_event: Optional[Callable[[str, dict], None]] = None,
    ):
        self.start_url = start_url
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.delay = delay
        self.respect_robots = respect_robots
        self.storage = storage or StoragePipeline()
        self.on_event = on_event

        # Determine allowed domain from start_url
        domain = urlparse(start_url).netloc
        self.frontier = UrlFrontier(
            allowed_domains={domain},
            max_depth=max_depth,
            politeness_delay=delay,
            respect_robots=respect_robots,
        )
        self.http_client = ResilientHttpClient()
        self.stats = CrawlStats(start_url=start_url)

    def _emit(self, event_type: str, data: dict):
        """Dispatches progress events to UI or logging handlers."""
        if self.on_event:
            self.on_event(event_type, data)

    def run(self) -> CrawlStats:
        """
        Executes the recursive crawl loop until max_pages is reached
        or the frontier queue is exhausted.
        """
        start_ts = time.time()
        self._emit("crawl_started", {"start_url": self.start_url, "max_pages": self.max_pages})

        # Step 1: Initialize robots.txt
        self.frontier.init_robots(self.start_url)

        # Step 2: Seed the frontier with the start URL
        self.frontier.add_url(self.start_url, depth=0)
        self.stats.urls_discovered += 1

        # Step 3: Main Crawl Loop
        try:
            while self.frontier.has_pending_urls() and self.stats.pages_visited < self.max_pages:
                item = self.frontier.get_next_url()
                if not item:
                    break
                current_url, depth = item

                self._emit("fetching", {
                    "url": current_url,
                    "depth": depth,
                    "visited": self.stats.pages_visited + 1,
                    "max_pages": self.max_pages,
                    "queue_size": self.frontier.queue_size,
                })

                # Fetch HTML
                html, status_code, error = self.http_client.fetch(current_url)

                if error or not html:
                    self.stats.errors_encountered += 1
                    self._emit("error", {"url": current_url, "error": error, "status": status_code})
                    continue

                self.stats.pages_visited += 1

                # Step 4: Parse Document
                soup = BeautifulSoup(html, "html.parser")
                is_detail = BookPageParser.is_detail_page(soup)

                if is_detail:
                    # Single book page -> extract book details
                    book = BookPageParser.parse_book_detail(html, current_url)
                    if book:
                        self.storage.save_item(book)
                        self.stats.items_scraped += 1
                        self._emit("item_scraped", {
                            "title": book.title,
                            "price": book.price,
                            "rating": book.rating,
                            "category": book.category,
                            "total_items": self.stats.items_scraped,
                        })

                # Step 5: Discover and Enqueue Links (if depth allows)
                if depth < self.max_depth:
                    links = BookPageParser.extract_links(html, current_url)
                    new_links_count = 0
                    for link in links:
                        if self.frontier.add_url(link, depth=depth + 1):
                            new_links_count += 1
                            self.stats.urls_discovered += 1

                    self._emit("links_discovered", {
                        "url": current_url,
                        "discovered_count": len(links),
                        "enqueued_count": new_links_count,
                        "frontier_size": self.frontier.queue_size,
                    })

        finally:
            self.http_client.close()
            end_ts = time.time()
            self.stats.end_time = datetime.now(timezone.utc).isoformat()
            self.stats.duration_seconds = round(end_ts - start_ts, 2)
            self._emit("crawl_completed", self.stats.model_dump())

        return self.stats
