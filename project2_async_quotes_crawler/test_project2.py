"""
Unit and Integration Test Suite for Project 2: Async Quotes Crawler.
Tests data validation, author HTML parsing, and relational async SQLite operations.
"""

import asyncio
import os
import shutil
import tempfile
import unittest

from project2_async_quotes_crawler.models import Author, Quote
from project2_async_quotes_crawler.html_parser import AuthorPageParser
from project2_async_quotes_crawler.storage import AsyncRelationalStorage


class TestProject2(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_quotes.db")
        self.storage = AsyncRelationalStorage(db_path=self.db_path)
        await self.storage.initialize()

    async def asyncTearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_models_cleaning(self):
        """Tests that text normalizers strip smart quotes and 'in ' prefixes."""
        q = Quote(
            text='“Two things are infinite: the universe and human stupidity.”',
            author_name="Albert Einstein",
            author_slug="Albert-Einstein",
            tags=["humanity", "wisdom"]
        )
        self.assertEqual(q.text, "Two things are infinite: the universe and human stupidity.")

        a = Author(
            slug="Albert-Einstein",
            name="Albert Einstein",
            born_location="in Ulm, Germany"
        )
        self.assertEqual(a.born_location, "Ulm, Germany")

    def test_author_html_parser(self):
        """Tests parsing of author profile markup."""
        sample_html = """
        <div class="author-details">
            <h3 class="author-title">J.K. Rowling</h3>
            <p><strong>Born:</strong> <span class="author-born-date">July 31, 1965</span>
               <span class="author-born-location">in Yate, South Gloucestershire, England</span>
            </p>
            <div class="author-description">
                British author best known for Harry Potter.
            </div>
        </div>
        """
        author = AuthorPageParser.parse(sample_html, slug="J-K-Rowling")
        self.assertIsNotNone(author)
        self.assertEqual(author.name, "J.K. Rowling")
        self.assertEqual(author.born_date, "July 31, 1965")
        self.assertEqual(author.born_location, "Yate, South Gloucestershire, England")
        self.assertTrue("Harry Potter" in author.description)

    async def test_relational_storage(self):
        """Tests relational storage, tags junction table, and analytics JOIN queries."""
        author = Author(
            slug="Steve-Jobs",
            name="Steve Jobs",
            born_date="February 24, 1955",
            born_location="San Francisco, California",
        )
        await self.storage.save_author(author)

        quote1 = Quote(
            text="Stay hungry, stay foolish.",
            author_name="Steve Jobs",
            author_slug="Steve-Jobs",
            tags=["inspiration", "life"],
        )
        quote2 = Quote(
            text="Innovation distinguishes between a leader and a follower.",
            author_name="Steve Jobs",
            author_slug="Steve-Jobs",
            tags=["innovation", "leadership"],
        )

        id1 = await self.storage.save_quote(quote1)
        id2 = await self.storage.save_quote(quote2)

        self.assertGreater(id1, 0)
        self.assertGreater(id2, id1)

        analytics = await self.storage.get_analytics()
        summary = analytics["summary"]
        self.assertEqual(summary["total_quotes"], 2)
        self.assertEqual(summary["total_authors"], 1)
        self.assertEqual(summary["total_tags"], 4)

        top_authors = analytics["top_authors"]
        self.assertEqual(len(top_authors), 1)
        self.assertEqual(top_authors[0]["name"], "Steve Jobs")
        self.assertEqual(top_authors[0]["quote_count"], 2)
        self.assertEqual(top_authors[0]["born_location"], "San Francisco, California")


if __name__ == "__main__":
    unittest.main()
