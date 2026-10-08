# Project 2: High-Concurrency Async Quotes & API Crawler

An advanced, high-performance web crawling project designed to teach **asynchronous concurrency (`asyncio` + `httpx`), reverse-engineering network APIs, and 3NF relational database architecture**.

---

## 🎯 What You Will Learn
1. **Asynchronous I/O for High Throughput**:
   - Web crawling is almost entirely **I/O bound** (waiting for HTTP responses).
   - In synchronous code, 100 requests at 0.5s each take **50 seconds**.
   - With an async event loop, requests run concurrently over persistent connection pools, finishing 100 requests in **under 3 seconds**.
2. **Reverse-Engineering Network APIs (The Professional Secret)**:
   - Modern websites frequently load data using client-side JavaScript (AJAX/Fetch) or infinite scroll.
   - *Beginner Trap*: Immediately reaching for heavy, slow browser automation tools like Selenium or Puppeteer (which consume 500MB+ RAM and render pixels you don't need).
   - *Pro Technique*: Open Developer Tools -> **Network Tab** -> Filter by `Fetch/XHR`. In `quotes.toscrape.com/scroll`, the browser queries `https://quotes.toscrape.com/api/quotes?page=1`!
   - Directly requesting this JSON API yields cleaner, faster, structured data with zero HTML parsing overhead for quotes.
3. **Concurrency Control with `asyncio.Semaphore`**:
   - Running asynchronous code without limits can spawn hundreds of simultaneous TCP connections, triggering server firewalls (HTTP 429 Too Many Requests) or causing denial-of-service.
   - Using `asyncio.Semaphore(5)` guarantees that **at most 5 requests** are active simultaneously.
4. **Concurrent Entity Enrichment (Hybrid Scraping)**:
   - While quotes are fetched from the JSON API, each unique author has a biographical detail page (`/author/{slug}/`).
   - The crawler spawns asynchronous tasks (`asyncio.create_task`) to crawl the author profiles in the background, extracting birth date and birthplace using BeautifulSoup.
5. **Relational Database Design (3rd Normal Form)**:
   - Demonstrates production-grade data modeling with `aiosqlite`:
     - `authors` table (slug, name, born_date, born_location, bio)
     - `quotes` table (text, author_slug [foreign key], page_number)
     - `tags` table (name)
     - `quote_tags` junction table (quote_id, tag_id)
   - Running relational SQL JOINs to answer business queries (e.g., "Which author birthplace produces the most quotes?").

---

## 🏗️ Architecture

```
                       ┌─────────────────────────┐
                       │   AsyncQuotesCrawler    │
                       └────────────┬────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │     AsyncHttpClient     │
                       │   (asyncio.Semaphore)   │
                       └────────────┬────────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
        ┌───────────────────┐               ┌───────────────────┐
        │  JSON API Worker  │               │   Author Worker   │
        │  /api/quotes?p=N  │               │  /author/{slug}/  │
        └─────────┬─────────┘               └─────────┬─────────┘
                  │                                   │
                  ▼                                   ▼
          ┌───────────────┐                   ┌───────────────┐
          │  Quote Item   │                   │  Author Item  │
          └───────┬───────┘                   └───────┬───────┘
                  │                                   │
                  └─────────────────┬─────────────────┘
                                    ▼
                      ┌───────────────────────────┐
                      │  AsyncRelationalStorage   │
                      ├───────────────────────────┤
                      │  • authors                │
                      │  • quotes                 │
                      │  • tags                   │
                      │  • quote_tags (junction)  │
                      └───────────────────────────┘
```

---

## 📂 Codebase Breakdown

| File | Purpose |
|---|---|
| [`models.py`](file:///home/sama/.gemini/antigravity/scratch/web_crawling_projects/project2_async_quotes_crawler/models.py) | Normalized relational schemas (`Author`, `Quote`, `AsyncCrawlStats`) with smart quote and location cleanup. |
| [`client.py`](file:///home/sama/.gemini/antigravity/scratch/web_crawling_projects/project2_async_quotes_crawler/client.py) | `httpx.AsyncClient` with connection pooling, `asyncio.Semaphore` rate limiter, and async exponential backoff. |
| [`html_parser.py`](file:///home/sama/.gemini/antigravity/scratch/web_crawling_projects/project2_async_quotes_crawler/html_parser.py) | Targeted HTML extractor for author biographical pages (`.author-title`, `.author-born-date`, etc.). |
| [`storage.py`](file:///home/sama/.gemini/antigravity/scratch/web_crawling_projects/project2_async_quotes_crawler/storage.py) | Asynchronous SQLite persistence using `aiosqlite`, relational foreign keys, indexes, and analytical JOIN queries. |
| [`crawler.py`](file:///home/sama/.gemini/antigravity/scratch/web_crawling_projects/project2_async_quotes_crawler/crawler.py) | Async orchestrator managing JSON pagination, background author enrichment tasks, and throughput metrics. |
| [`main.py`](file:///home/sama/.gemini/antigravity/scratch/web_crawling_projects/project2_async_quotes_crawler/main.py) | CLI executing `asyncio.run()` with live Rich tables and throughput reporting (quotes/sec). |
| [`test_project2.py`](file:///home/sama/.gemini/antigravity/scratch/web_crawling_projects/project2_async_quotes_crawler/test_project2.py) | Test suite covering models, HTML parsing, and relational async SQLite operations. |

---

## 🚀 How to Run

From the root project directory:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the async crawler (crawls 3 API pages with max 5 concurrent connections)
python project2_async_quotes_crawler/main.py --max-pages 3 --concurrency 5

# High-speed crawl without author enrichment
python project2_async_quotes_crawler/main.py --max-pages 5 --concurrency 10 --no-enrich
```

### CLI Arguments:
- `--max-pages`: Maximum API pages to fetch (default: `3`)
- `--concurrency`: Max concurrent HTTP connections allowed (default: `5`)
- `--db`: Relational SQLite database destination (default: `data/quotes_relational.db`)
- `--no-enrich`: Skip author profile HTML enrichment (pure API mode)
