# Project 1: Polite Recursive Books Crawler

An end-to-end web crawler and data extraction engine designed to teach foundational **static web crawling, graph traversal algorithms, DOM extraction, and database persistence**.

---

## 🎯 What You Will Learn
1. **Web Crawling vs Web Scraping**:
   - *Crawling* is discovering, tracking, and traversing links across a graph of web pages.
   - *Scraping* is extracting structured fields (title, price, rating) from the HTML of an individual page.
2. **The URL Frontier & Graph Algorithms**:
   - Managing a **Breadth-First Search (BFS)** queue using `collections.deque`.
   - Why BFS is preferred over DFS (Depth-First Search) for web crawling (avoids rabbit holes and prioritizes shallow, authoritative pages).
   - Enforcing strict `max_depth` and `max_pages` bounds.
3. **Canonicalization & Deduplication**:
   - Stripping URL fragments (`#section`) with `urllib.parse.urldefrag`.
   - Resolving relative paths (`../catalogue/book.html`) to absolute URLs with `urllib.parse.urljoin`.
   - Maintaining an in-memory `visited` hash set to prevent infinite loops and re-crawling.
4. **Politeness & `robots.txt`**:
   - Checking server crawling rules with `urllib.robotparser.RobotFileParser`.
   - Applying politeness delays with **random jitter** to prevent server strain.
5. **DOM Parsing with BeautifulSoup**:
   - CSS selectors (`article.product_pod`, `div.product_main h1`, `table.table-striped`).
   - Extracting text, attribute values (`href`, `src`), and handling missing elements safely.
6. **Data Validation & Persistence**:
   - Pydantic models for type validation and automatic type coercion (e.g., converting `"£51.77"` to `51.77` float, `"star-rating Three"` to `3` integer).
   - Storing into both **SQLite** (with indexes and `ON CONFLICT DO UPDATE` upserts) and **JSON Lines (`.jsonl`)**.

---

## 🏗️ Architecture

```
                      ┌──────────────────────┐
                      │    Start Seed URL    │
                      └──────────┬───────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │     UrlFrontier       │◄───────────────────────┐
                     │ (BFS Queue + Visited) │                        │
                     └──────────┬────────────┘                        │
                                │  Pop next URL & apply delay         │
                                ▼                                     │
                     ┌───────────────────────┐                        │
                     │  ResilientHttpClient  │                        │
                     │ (Retry + User-Agent)  │                        │
                     └──────────┬────────────┘                        │
                                │  Fetch HTML                         │
                                ▼                                     │
                     ┌───────────────────────┐                        │
                     │    BookPageParser     │                        │
                     └────┬─────────────┬────┘                        │
                          │             │                             │
          Is Product Page │             │ Discovered Links            │
                          ▼             └─────────────────────────────┘
                ┌──────────────────┐
                │     BookItem     │
                │ (Pydantic Model) │
                └─────────┬────────┘
                          ▼
                ┌──────────────────┐
                │ StoragePipeline  │
                ├──────────────────┤
                │ • books.db (SQL) │
                │ • books.jsonl    │
                └──────────────────┘
```

---

## 📂 Codebase Breakdown

| File | Purpose |
|---|---|
| [`models.py`](file:///home/sama/.gemini/antigravity/scratch/web_crawling_projects/project1_books_crawler/models.py) | Pydantic schema (`BookItem`, `CrawlStats`) with field validators for currency, rating words, and inventory numbers. |
| [`frontier.py`](file:///home/sama/.gemini/antigravity/scratch/web_crawling_projects/project1_books_crawler/frontier.py) | BFS queue, visited set, URL canonicalizer, robots.txt validator, and jittered rate limiter. |
| [`http_client.py`](file:///home/sama/.gemini/antigravity/scratch/web_crawling_projects/project1_books_crawler/http_client.py) | Requests Session with connection pooling and `urllib3.util.Retry` exponential backoff on HTTP 429/5xx. |
| [`parser.py`](file:///home/sama/.gemini/antigravity/scratch/web_crawling_projects/project1_books_crawler/parser.py) | BeautifulSoup parser targeting listing cards, pagination next buttons, and product tables. |
| [`storage.py`](file:///home/sama/.gemini/antigravity/scratch/web_crawling_projects/project1_books_crawler/storage.py) | SQLite database manager with upsert logic, indexes, and analytical summary queries. |
| [`crawler.py`](file:///home/sama/.gemini/antigravity/scratch/web_crawling_projects/project1_books_crawler/crawler.py) | Central orchestrator that links the frontier, HTTP client, parser, and storage. |
| [`main.py`](file:///home/sama/.gemini/antigravity/scratch/web_crawling_projects/project1_books_crawler/main.py) | Interactive CLI featuring rich console tables and real-time event streaming. |
| [`test_project1.py`](file:///home/sama/.gemini/antigravity/scratch/web_crawling_projects/project1_books_crawler/test_project1.py) | Automated test suite verifying data validation, frontier rules, parsing, and SQL operations. |

---

## 🚀 How to Run

From the root project directory:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the crawler (crawls 10 pages with a 0.3-second politeness delay)
python project1_books_crawler/main.py --max-pages 10 --delay 0.3

# Custom crawl parameters
python project1_books_crawler/main.py --max-pages 25 --max-depth 3 --db data/my_books.db
```

### CLI Arguments:
- `--start-url`: Seed URL (defaults to `https://books.toscrape.com/`)
- `--max-pages`: Maximum pages to crawl (default: `10`)
- `--max-depth`: Max link hops from start URL (default: `2`)
- `--delay`: Politeness sleep duration in seconds (default: `0.3`)
- `--db`: SQLite database destination (default: `data/books.db`)
- `--jsonl`: JSON Lines streaming destination (default: `data/books.jsonl`)
- `--no-robots`: Skip robots.txt parsing (not recommended for production)
