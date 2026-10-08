"""
Data models and schemas for Project 1: Books Crawler.

Demonstrates:
- Pydantic BaseModel for automatic schema validation and type coercion.
- Field validators for parsing currency strings, star rating text, and stock counts.
"""

from datetime import datetime, timezone
import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator, HttpUrl


RATING_MAP = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}


class BookItem(BaseModel):
    """
    Structured, validated representation of a scraped book item.
    """
    url: str
    title: str = Field(..., min_length=1)
    price: float = Field(..., ge=0.0, description="Price in GBP as float")
    rating: int = Field(default=0, ge=0, le=5, description="Star rating between 0 and 5")
    availability: str = Field(default="In stock")
    stock_quantity: int = Field(default=1, ge=0, description="Parsed inventory count")
    upc: str = Field(default="", description="Universal Product Code (UPC)")
    category: str = Field(default="Unknown", description="Book category from breadcrumb")
    description: Optional[str] = Field(default=None, description="Product description text")
    image_url: Optional[str] = Field(default=None, description="Absolute image URL")
    scraped_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 scraping timestamp"
    )

    @field_validator("price", mode="before")
    @classmethod
    def parse_price(cls, v):
        """Extract float from price strings like '£51.77' or '$12.50'."""
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            clean = re.sub(r"[^\d.]", "", v)
            if clean:
                return float(clean)
        return 0.0

    @field_validator("rating", mode="before")
    @classmethod
    def parse_rating(cls, v):
        """Convert rating classes like 'star-rating Three' to integer 3."""
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            text = v.lower().strip()
            for word, num in RATING_MAP.items():
                if word in text:
                    return num
            if text.isdigit():
                return int(text)
        return 0

    @field_validator("availability", mode="before")
    @classmethod
    def parse_availability(cls, v):
        """Normalize availability to 'In stock' or 'Out of stock'."""
        if isinstance(v, str):
            if "in stock" in v.lower():
                return "In stock"
            if "out of stock" in v.lower():
                return "Out of stock"
        return str(v) if v else "Unknown"

    @field_validator("stock_quantity", mode="before")
    @classmethod
    def parse_stock_quantity(cls, v):
        """Extract integer count from text like 'In stock (22 available)'."""
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            match = re.search(r"\((\d+)\s+available\)", v)
            if match:
                return int(match.group(1))
            if "in stock" in v.lower():
                return 1
        return 0


class CrawlStats(BaseModel):
    """
    Real-time statistics tracking for the crawling run.
    """
    start_url: str
    pages_visited: int = 0
    items_scraped: int = 0
    urls_discovered: int = 0
    errors_encountered: int = 0
    start_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: Optional[str] = None
    duration_seconds: float = 0.0
