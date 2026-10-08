"""
Async Crawler Orchestrator for Project 2.

Demonstrates:
- High-throughput asynchronous crawling combining dynamic JSON API & HTML parsing.
- Concurrent entity enrichment (Author bio scraping concurrent with Quotes stream).
- Deduplicated author crawling using an in-memory set.
- Graceful shutdown and live event streaming.
"""

import asyncio
import logging
import time
from typing import Callable, Optional, Set
from urllib.parse import urljoin

from .client import AsyncHttpClient
from .html_parser import AuthorPageParser
from .models import AsyncCrawlStats, Author, Quote
from .storage import AsyncRelationalStorage

logger = logging.getLogger(__name__)


class AsyncQuotesCrawler:
    """
    High-concurrency crawler that leverages quotes.toscrape.com's dynamic API
    and concurrently enriches quote records with author biographies.
    """

    BASE_URL = "https://quotes.toscrape.com"
    API_URL_TEMPLATE = "https://quotes.toscrape.com/api/quotes?page={page}"

    def __init__(
        self,
        max_pages: int = 5,
        max_concurrency: int = 5,
        enrich_authors: bool = True,
        storage: Optional[AsyncRelationalStorage] = None,
        on_event: Optional[Callable[[str, dict], None]] = None,
    ):
        self.max_pages = max_pages
        self.max_concurrency = max_concurrency
        self.enrich_authors = enrich_authors
        self.storage = storage or AsyncRelationalStorage()
        self.on_event = on_event

        self.http_client = AsyncHttpClient(max_concurrency=max_concurrency)
        self.seen_author_slugs: Set[str] = set()
        self.stats = AsyncCrawlStats()

    def _emit(self, event_type: str, data: dict):
        if self.on_event:
            self.on_event(event_type, data)

    async def _fetch_and_enrich_author(self, slug: str, goodreads_link: Optional[str] = None):
        """Fetches and parses the author's biographical profile page asynchronously."""
        author_url = f"{self.BASE_URL}/author/{slug}/"
        html = await self.http_client.fetch_html(author_url)
        if not html:
            self.stats.network_errors += 1
            return

        author = AuthorPageParser.parse(html, slug=slug, goodreads_link=goodreads_link)
        if author:
            await self.storage.save_author(author)
            self.stats.authors_enriched += 1
            self._emit("author_enriched", {
                "name": author.name,
                "location": author.born_location or "Unknown",
                "date": author.born_date or "Unknown",
            })

    async def _process_page(self, page_num: int) -> bool:
        """
        Fetches a single page of quotes from the JSON API, stores quotes,
        and triggers concurrent author enrichment.
        Returns True if more pages exist (has_next), False otherwise.
        """
        api_url = self.API_URL_TEMPLATE.format(page=page_num)
        self._emit("fetching_page", {"page": page_num, "url": api_url})

        data = await self.http_client.fetch_json(api_url)
        if not data:
            self.stats.network_errors += 1
            return False

        quotes_data = data.get("quotes", [])
        self.stats.pages_crawled += 1

        author_tasks = []

        for item in quotes_data:
            author_info = item.get("author", {})
            author_name = author_info.get("name", "Unknown")
            author_slug = author_info.get("slug", "")
            goodreads = author_info.get("goodreads_link")
            raw_text = item.get("text", "")
            tags = item.get("tags", [])

            quote = Quote(
                text=raw_text,
                author_name=author_name,
                author_slug=author_slug,
                tags=tags,
                page_number=page_num,
            )

            # Save quote to database
            await self.storage.save_quote(quote)
            self.stats.quotes_extracted += 1
            self.stats.tags_extracted += len(tags)

            self._emit("quote_scraped", {
                "text": quote.text[:60] + "...",
                "author": author_name,
                "tags_count": len(tags),
                "total_quotes": self.stats.quotes_extracted,
            })

            # Check if author biographical data needs enrichment
            if self.enrich_authors and author_slug and author_slug not in self.seen_author_slugs:
                self.seen_author_slugs.add(author_slug)
                # Create concurrent async task for author profile
                task = asyncio.create_task(
                    self._fetch_and_enrich_author(author_slug, goodreads)
                )
                author_tasks.append(task)

        # Await any spawned author enrichment tasks for this batch
        if author_tasks:
            await asyncio.gather(*author_tasks, return_exceptions=True)

        return data.get("has_next", False)

    async def run(self) -> AsyncCrawlStats:
        """
        Executes the async crawling lifecycle across pages.
        """
        start_ts = time.time()
        await self.storage.initialize()
        self._emit("crawl_started", {
            "max_pages": self.max_pages,
            "concurrency": self.max_concurrency,
            "enrich_authors": self.enrich_authors,
        })

        try:
            for page in range(1, self.max_pages + 1):
                has_next = await self._process_page(page)
                if not has_next:
                    self._emit("no_more_pages", {"last_page": page})
                    break

        finally:
            await self.http_client.aclose()
            end_ts = time.time()
            elapsed = max(end_ts - start_ts, 0.001)
            self.stats.end_time = end_ts
            self.stats.elapsed_seconds = round(elapsed, 2)
            self.stats.quotes_per_second = round(self.stats.quotes_extracted / elapsed, 2)
            self._emit("crawl_completed", self.stats.model_dump())

        return self.stats
