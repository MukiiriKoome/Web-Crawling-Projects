"""
Comprehensive Test Suite for Project 1: Books Crawler.
Verifies parsing logic, frontier queues, pydantic data validation, and storage pipeline.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from project1_books_crawler.models import BookItem
from project1_books_crawler.frontier import UrlFrontier
from project1_books_crawler.parser import BookPageParser
from project1_books_crawler.storage import StoragePipeline


class TestProject1(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_books.db")
        self.jsonl_path = os.path.join(self.test_dir, "test_books.jsonl")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_model_field_validators(self):
        """Tests parsing of currency, star ratings, and inventory quantities."""
        item = BookItem(
            url="https://books.toscrape.com/catalogue/test_1/index.html",
            title="Clean Code",
            price="£42.50",
            rating="star-rating Four",
            availability="In stock (19 available)",
            stock_quantity="In stock (19 available)",
            category="Programming"
        )
        self.assertEqual(item.price, 42.50)
        self.assertEqual(item.rating, 4)
        self.assertEqual(item.stock_quantity, 19)
        self.assertEqual(item.availability, "In stock")

    def test_frontier_canonicalization_and_deduplication(self):
        """Tests that URL fragments are stripped and visited URLs are not duplicated."""
        frontier = UrlFrontier(allowed_domains={"books.toscrape.com"}, max_depth=2, respect_robots=False)

        # First addition
        added_1 = frontier.add_url("https://books.toscrape.com/catalogue/page-1.html#section1", depth=0)
        self.assertTrue(added_1)

        # Same URL with different fragment or trailing slash -> should be duplicate
        added_2 = frontier.add_url("https://books.toscrape.com/catalogue/page-1.html#reviews", depth=0)
        self.assertFalse(added_2, "Frontier should deduplicate URLs regardless of fragment")

        # External domain -> should be rejected
        added_external = frontier.add_url("https://malicious-site.com/index.html", depth=0)
        self.assertFalse(added_external, "Frontier must reject off-domain URLs")

        # Exceeding depth -> should be rejected
        added_deep = frontier.add_url("https://books.toscrape.com/catalogue/deep.html", depth=3)
        self.assertFalse(added_deep, "Frontier must respect max_depth")

    def test_parser_extract_detail(self):
        """Tests HTML parsing on realistic product page markup."""
        sample_html = """
        <!DOCTYPE html>
        <html>
        <body>
            <ul class="breadcrumb">
                <li><a href="../index.html">Home</a></li>
                <li><a href="../category/books_1/index.html">Books</a></li>
                <li><a href="../category/books/travel_2/index.html">Travel</a></li>
                <li class="active">A Journey Through Time</li>
            </ul>
            <article class="product_page">
                <div class="product_main">
                    <h1>A Journey Through Time</h1>
                    <p class="price_color">£34.99</p>
                    <p class="star-rating Three"></p>
                    <p class="availability"><i class="icon-ok"></i> In stock (14 available)</p>
                </div>
                <div id="product_description" class="sub-heading"><h2>Product Description</h2></div>
                <p>An amazing travel memoir.</p>
                <div id="product_gallery"><img src="../../media/book1.jpg" alt="cover"/></div>
                <table class="table table-striped">
                    <tr><th>UPC</th><td>abc123upc</td></tr>
                    <tr><th>Availability</th><td>In stock (14 available)</td></tr>
                </table>
            </article>
        </body>
        </html>
        """
        item = BookPageParser.parse_book_detail(sample_html, "https://books.toscrape.com/catalogue/travel_1/index.html")
        self.assertIsNotNone(item)
        self.assertEqual(item.title, "A Journey Through Time")
        self.assertEqual(item.price, 34.99)
        self.assertEqual(item.rating, 3)
        self.assertEqual(item.category, "Travel")
        self.assertEqual(item.upc, "abc123upc")
        self.assertEqual(item.description, "An amazing travel memoir.")
        self.assertTrue(item.image_url.endswith("/media/book1.jpg"))

    def test_storage_pipeline_sqlite_and_jsonl(self):
        """Tests SQLite upsert, JSONL writing, and analytical summary queries."""
        pipeline = StoragePipeline(db_path=self.db_path, jsonl_path=self.jsonl_path)
        book1 = BookItem(
            url="https://books.toscrape.com/catalogue/book1/index.html",
            title="Book 1",
            price="£20.00",
            rating=5,
            category="Fiction",
            stock_quantity=10,
        )
        book2 = BookItem(
            url="https://books.toscrape.com/catalogue/book2/index.html",
            title="Book 2",
            price="£30.00",
            rating=3,
            category="Fiction",
            stock_quantity=5,
        )
        pipeline.save_item(book1)
        pipeline.save_item(book2)

        summary = pipeline.get_summary()
        self.assertEqual(summary["total_books"], 2)
        self.assertEqual(summary["avg_price"], 25.0)
        self.assertEqual(summary["avg_rating"], 4.0)

        # Verify JSON Lines file exists and has 2 lines
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 2)


if __name__ == "__main__":
    unittest.main()
