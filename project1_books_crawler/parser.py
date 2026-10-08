"""
HTML Parsing and Data Extraction Module for Project 1.

Demonstrates:
- DOM traversal with BeautifulSoup4.
- CSS Selectors for robust element targeting.
- URL resolution (relative to absolute via urllib.parse.urljoin).
- Link extraction with filtering (listing pagination vs product pages).
- Graceful degradation when optional HTML elements are absent.
"""

from typing import List, Optional, Tuple
from urllib.parse import urljoin, urldefrag
from bs4 import BeautifulSoup

from .models import BookItem


class BookPageParser:
    """
    Parses HTML documents from books.toscrape.com, distinguishing between:
    - Catalog/Listing pages (contains multiple book cards, pagination links)
    - Detail/Product pages (contains single book specs, table, full description)
    """

    @staticmethod
    def clean_url(base_url: str, relative_url: str) -> str:
        """
        Converts a relative URL to an absolute URL and removes fragment identifiers (#).
        Example: '../../catalogue/page.html#reviews' -> 'https://books.toscrape.com/catalogue/page.html'
        """
        full_url = urljoin(base_url, relative_url.strip())
        defragged_url, _ = urldefrag(full_url)
        return defragged_url

    @classmethod
    def is_detail_page(cls, soup: BeautifulSoup) -> bool:
        """
        Detects if current page is a single book detail page.
        Detail pages have an element `<div id="product_description">` or `<article class="product_page">`.
        """
        return soup.find("article", class_="product_page") is not None

    @classmethod
    def extract_links(cls, html: str, current_url: str) -> List[str]:
        """
        Discovers all crawlable links on the page:
        - Next page pagination (`li.next > a`)
        - Book detail links (`article.product_pod h3 a`)
        - Category links (`.side_categories a`)

        Returns a list of normalized, absolute URLs.
        """
        soup = BeautifulSoup(html, "html.parser")
        discovered_urls: List[str] = []

        # 1. Discover links inside book cards
        for pod in soup.select("article.product_pod h3 a"):
            href = pod.get("href")
            if href:
                discovered_urls.append(cls.clean_url(current_url, href))

        # 2. Discover pagination next-page link
        next_button = soup.select_one("li.next a")
        if next_button and next_button.get("href"):
            discovered_urls.append(cls.clean_url(current_url, next_button["href"]))

        # 3. Discover category links from the sidebar (if any)
        for cat_link in soup.select(".side_categories ul li a"):
            href = cat_link.get("href")
            if href:
                discovered_urls.append(cls.clean_url(current_url, href))

        # Return unique URLs while preserving discovery order
        return list(dict.fromkeys(discovered_urls))

    @classmethod
    def parse_book_detail(cls, html: str, page_url: str) -> Optional[BookItem]:
        """
        Extracts structured book details from a book's detail page.
        """
        soup = BeautifulSoup(html, "html.parser")
        article = soup.find("article", class_="product_page")
        if not article:
            return None

        # Title
        title_el = article.select_one(".product_main h1")
        title = title_el.get_text(strip=True) if title_el else "Unknown Title"

        # Price
        price_el = article.select_one(".product_main .price_color")
        price_raw = price_el.get_text(strip=True) if price_el else "0.0"

        # Star Rating
        rating_el = article.select_one(".product_main .star-rating")
        rating_classes = " ".join(rating_el.get("class", [])) if rating_el else ""

        # Availability and Stock Quantity
        avail_el = article.select_one(".product_main .availability")
        avail_raw = avail_el.get_text(strip=True) if avail_el else ""

        # Category from Breadcrumb: Home > Books > [Category] > [Title]
        category = "Unknown"
        breadcrumbs = soup.select("ul.breadcrumb li a")
        if len(breadcrumbs) >= 3:
            category = breadcrumbs[2].get_text(strip=True)

        # Description
        desc_heading = soup.find("div", id="product_description")
        description = None
        if desc_heading:
            p_desc = desc_heading.find_next_sibling("p")
            if p_desc:
                description = p_desc.get_text(strip=True)

        # Image URL
        image_url = None
        img_el = article.select_one("#product_gallery img, .carousel img")
        if img_el and img_el.get("src"):
            image_url = cls.clean_url(page_url, img_el["src"])

        # Table Information (UPC, Tax, etc.)
        table_data = {}
        for row in soup.select("table.table-striped tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td:
                key = th.get_text(strip=True).lower()
                val = td.get_text(strip=True)
                table_data[key] = val

        upc = table_data.get("upc", "")
        # Table availability often has exact stock count
        table_avail = table_data.get("availability", avail_raw)

        return BookItem(
            url=page_url,
            title=title,
            price=price_raw,
            rating=rating_classes,
            availability="In stock" if "in stock" in table_avail.lower() else "Out of stock",
            stock_quantity=table_avail,
            upc=upc,
            category=category,
            description=description,
            image_url=image_url
        )
