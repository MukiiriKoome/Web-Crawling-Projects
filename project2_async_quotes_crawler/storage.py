"""
Asynchronous Relational Persistence Layer using aiosqlite.

Demonstrates:
- 3rd Normal Form (3NF) relational schema for web scraping entities:
    - Authors (1) <----> (M) Quotes
    - Quotes  (M) <----> (M) Tags (via quote_tags junction table)
- Asynchronous database operations with connection management.
- Analytical relational JOIN queries.
"""

from pathlib import Path
from typing import Any, Dict, List
import aiosqlite

from .models import Author, Quote


class AsyncRelationalStorage:
    """
    Manages an asynchronous SQLite database storing quotes, authors, and tags.
    """

    def __init__(self, db_path: str = "data/quotes_relational.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Creates tables, foreign keys, and indexes."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")

            # 1. Authors Table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS authors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    born_date TEXT,
                    born_location TEXT,
                    description TEXT,
                    goodreads_link TEXT,
                    scraped_at TEXT NOT NULL
                )
            """)

            # 2. Quotes Table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    author_slug TEXT NOT NULL,
                    page_number INTEGER,
                    scraped_at TEXT NOT NULL,
                    FOREIGN KEY (author_slug) REFERENCES authors(slug)
                )
            """)

            # 3. Tags Table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            """)

            # 4. Many-to-Many Junction Table (Quote <-> Tag)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS quote_tags (
                    quote_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (quote_id, tag_id),
                    FOREIGN KEY (quote_id) REFERENCES quotes(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                )
            """)

            # Performance Indexes
            await db.execute("CREATE INDEX IF NOT EXISTS idx_quotes_author ON quotes(author_slug)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)")
            await db.commit()

    async def save_author(self, author: Author):
        """Inserts or updates an author biographical record."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO authors (
                    slug, name, born_date, born_location, description, goodreads_link, scraped_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    born_date = excluded.born_date,
                    born_location = excluded.born_location,
                    description = excluded.description,
                    goodreads_link = excluded.goodreads_link
            """, (
                author.slug,
                author.name,
                author.born_date,
                author.born_location,
                author.description,
                author.goodreads_link,
                author.scraped_at,
            ))
            await db.commit()

    async def save_quote(self, quote: Quote) -> int:
        """
        Persists a quote and links its tags transactionally.
        Returns the inserted quote ID.
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")

            # Ensure placeholder author exists so foreign key doesn't fail before author crawl completes
            await db.execute("""
                INSERT OR IGNORE INTO authors (slug, name, scraped_at)
                VALUES (?, ?, ?)
            """, (quote.author_slug, quote.author_name, quote.scraped_at))

            # Insert Quote
            cursor = await db.execute("""
                INSERT INTO quotes (text, author_slug, page_number, scraped_at)
                VALUES (?, ?, ?, ?)
            """, (quote.text, quote.author_slug, quote.page_number, quote.scraped_at))
            quote_id = cursor.lastrowid

            # Insert Tags and link them
            for tag_name in quote.tags:
                clean_tag = tag_name.strip().lower()
                if not clean_tag:
                    continue

                # Insert Tag if new
                await db.execute(
                    "INSERT OR IGNORE INTO tags (name) VALUES (?)",
                    (clean_tag,)
                )

                # Fetch Tag ID
                tag_cursor = await db.execute("SELECT id FROM tags WHERE name = ?", (clean_tag,))
                tag_row = await tag_cursor.fetchone()
                if tag_row:
                    tag_id = tag_row[0]
                    # Link in junction table
                    await db.execute(
                        "INSERT OR IGNORE INTO quote_tags (quote_id, tag_id) VALUES (?, ?)",
                        (quote_id, tag_id)
                    )

            await db.commit()
            return quote_id

    async def get_analytics(self) -> Dict[str, Any]:
        """
        Runs relational JOIN analytical queries on stored data.
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Counts
            counts_cursor = await db.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM quotes) as total_quotes,
                    (SELECT COUNT(*) FROM authors) as total_authors,
                    (SELECT COUNT(*) FROM tags) as total_tags
            """)
            counts = dict(await counts_cursor.fetchone() or {})

            # Top Quoted Authors with their birthplaces
            authors_cursor = await db.execute("""
                SELECT 
                    a.name, 
                    a.born_location, 
                    COUNT(q.id) as quote_count
                FROM authors a
                JOIN quotes q ON a.slug = q.author_slug
                GROUP BY a.slug
                ORDER BY quote_count DESC
                LIMIT 5
            """)
            top_authors = [dict(row) for row in await authors_cursor.fetchall()]

            # Top Tags
            tags_cursor = await db.execute("""
                SELECT t.name, COUNT(qt.quote_id) as count
                FROM tags t
                JOIN quote_tags qt ON t.id = qt.tag_id
                GROUP BY t.id
                ORDER BY count DESC
                LIMIT 6
            """)
            top_tags = [dict(row) for row in await tags_cursor.fetchall()]

            # Sample Quotes with Authors
            sample_cursor = await db.execute("""
                SELECT q.text, a.name, a.born_location
                FROM quotes q
                JOIN authors a ON q.author_slug = a.slug
                ORDER BY q.id DESC
                LIMIT 3
            """)
            sample_quotes = [dict(row) for row in await sample_cursor.fetchall()]

            return {
                "summary": counts,
                "top_authors": top_authors,
                "top_tags": top_tags,
                "sample_quotes": sample_quotes,
            }
