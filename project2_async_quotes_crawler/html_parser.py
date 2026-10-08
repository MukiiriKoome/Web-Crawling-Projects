"""
HTML Parsing Module for Author Profiles in Project 2.

Demonstrates:
- Targeted DOM extraction for secondary entity enrichment.
- Cleaning biographical text and birth information.
"""

from typing import Optional
from bs4 import BeautifulSoup

from .models import Author


class AuthorPageParser:
    """
    Parses author biographical detail pages on quotes.toscrape.com.
    """

    @classmethod
    def parse(cls, html: str, slug: str, goodreads_link: Optional[str] = None) -> Optional[Author]:
        soup = BeautifulSoup(html, "html.parser")

        title_el = soup.select_one(".author-title")
        if not title_el:
            return None
        name = title_el.get_text(strip=True)

        born_date_el = soup.select_one(".author-born-date")
        born_date = born_date_el.get_text(strip=True) if born_date_el else None

        born_loc_el = soup.select_one(".author-born-location")
        born_loc = born_loc_el.get_text(strip=True) if born_loc_el else None

        desc_el = soup.select_one(".author-description")
        description = desc_el.get_text(strip=True) if desc_el else None

        return Author(
            slug=slug,
            name=name,
            born_date=born_date,
            born_location=born_loc,
            description=description,
            goodreads_link=goodreads_link,
        )
