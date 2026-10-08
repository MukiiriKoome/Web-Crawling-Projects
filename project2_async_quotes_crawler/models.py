"""
Data models and schemas for Project 2: High-Concurrency Async Crawler.

Demonstrates:
- Normalized relational schemas (Author, Quote, Tag) using Pydantic.
- Automatic text cleaning and normalization (stripping smart quotes, whitespace).
- Crawl telemetry and performance metrics models.
"""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class Author(BaseModel):
    """
    Biographical profile of a quote author, fetched and enriched from their profile page.
    """
    slug: str = Field(..., description="Unique URL slug, e.g. 'Albert-Einstein'")
    name: str = Field(..., min_length=1)
    born_date: Optional[str] = Field(default=None, description="Birth date, e.g. 'March 14, 1879'")
    born_location: Optional[str] = Field(default=None, description="Birthplace, e.g. 'in Ulm, Germany'")
    description: Optional[str] = Field(default=None, description="Biographical overview")
    goodreads_link: Optional[str] = None
    scraped_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @field_validator("born_location", mode="before")
    @classmethod
    def clean_location(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.lower().startswith("in "):
                v = v[3:].strip()
            return v
        return v


class Quote(BaseModel):
    """
    Extracted quote item with author reference and tags.
    """
    text: str = Field(..., min_length=1)
    author_name: str
    author_slug: str
    tags: List[str] = Field(default_factory=list)
    page_number: int = 1
    scraped_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @field_validator("text", mode="before")
    @classmethod
    def clean_text(cls, v):
        if isinstance(v, str):
            # Clean curly quotes and excess whitespace
            v = v.strip().strip('“"”').strip()
            return v
        return v


class AsyncCrawlStats(BaseModel):
    """
    High-resolution telemetry for asynchronous crawling performance.
    """
    pages_crawled: int = 0
    quotes_extracted: int = 0
    authors_enriched: int = 0
    tags_extracted: int = 0
    network_errors: int = 0
    start_time: float = Field(default_factory=datetime.now().timestamp)
    end_time: Optional[float] = None
    elapsed_seconds: float = 0.0
    quotes_per_second: float = 0.0
