"""
Data Persistence and Pipeline Module for Project 1.

Demonstrates:
- Dual-target storage: SQLite relational database & JSON Lines (.jsonl).
- Idempotent upsert operations (ON CONFLICT DO UPDATE).
- Schema creation with proper SQL column types, constraints, and indexes.
- Analytical summary queries on scraped data.
"""

import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional

from .models import BookItem


class StoragePipeline:
    """
    Handles buffering and persisting extracted items into SQLite and JSON Lines.
    """

    def __init__(self, db_path: str = "books.db", jsonl_path: Optional[str] = "books.jsonl"):
        self.db_path = Path(db_path)
        self.jsonl_path = Path(jsonl_path) if jsonl_path else None

        # Ensure parent directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if self.jsonl_path:
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_sqlite()

    def _init_sqlite(self):
        """Initializes SQLite tables and performance indexes."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    price REAL NOT NULL,
                    rating INTEGER NOT NULL,
                    availability TEXT NOT NULL,
                    stock_quantity INTEGER NOT NULL,
                    upc TEXT,
                    category TEXT,
                    description TEXT,
                    image_url TEXT,
                    scraped_at TEXT NOT NULL
                )
            """)

            # Create indexes for fast querying by category, price, rating
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_category ON books(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_price ON books(price)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_rating ON books(rating)")
            conn.commit()

    def save_item(self, item: BookItem) -> bool:
        """
        Saves a validated BookItem to both SQLite and JSONL.
        Returns True if newly inserted, False if updated/skipped.
        """
        # 1. SQLite Upsert
        inserted = False
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO books (
                    url, title, price, rating, availability, stock_quantity,
                    upc, category, description, image_url, scraped_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title=excluded.title,
                    price=excluded.price,
                    rating=excluded.rating,
                    availability=excluded.availability,
                    stock_quantity=excluded.stock_quantity,
                    upc=excluded.upc,
                    category=excluded.category,
                    description=excluded.description,
                    image_url=excluded.image_url,
                    scraped_at=excluded.scraped_at
            """, (
                item.url,
                item.title,
                item.price,
                item.rating,
                item.availability,
                item.stock_quantity,
                item.upc,
                item.category,
                item.description,
                item.image_url,
                item.scraped_at,
            ))
            inserted = cursor.rowcount > 0
            conn.commit()

        # 2. JSON Lines streaming append
        if self.jsonl_path:
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(item.model_dump_json() + "\n")

        return inserted

    def get_summary(self) -> Dict[str, Any]:
        """
        Runs analytical aggregate queries to provide a summary of scraped data.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    COUNT(*) as total_books,
                    ROUND(AVG(price), 2) as avg_price,
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    ROUND(AVG(rating), 2) as avg_rating,
                    COUNT(DISTINCT category) as total_categories
                FROM books
            """)
            summary = dict(cursor.fetchone() or {})

            # Top categories
            cursor.execute("""
                SELECT category, COUNT(*) as count, ROUND(AVG(price), 2) as avg_price
                FROM books
                GROUP BY category
                ORDER BY count DESC
                LIMIT 5
            """)
            summary["top_categories"] = [dict(row) for row in cursor.fetchall()]

            return summary

    def get_recent_items(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Returns the most recently scraped items."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT title, category, price, rating, availability FROM books ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
