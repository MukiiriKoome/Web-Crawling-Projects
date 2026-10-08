"""
Command-Line Interface (CLI) for Project 2: High-Concurrency Async Crawler.

Demonstrates:
- Running asyncio event loops with Python's asyncio.run.
- Live streaming async extraction events to Rich console.
- Displaying relational data and SQL JOIN query results.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Support running directly or as a module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from project2_async_quotes_crawler.crawler import AsyncQuotesCrawler
from project2_async_quotes_crawler.storage import AsyncRelationalStorage

console = Console()


def handle_event(event_type: str, data: dict):
    """Callback to render async events in the console."""
    if event_type == "crawl_started":
        console.print(
            f"[bold magenta]▶ Starting Async Crawl[/] (Pages: {data['max_pages']} | "
            f"Concurrency Limit: {data['concurrency']} | Enrich Authors: {data['enrich_authors']})"
        )
    elif event_type == "fetching_page":
        console.print(f" [cyan]•[/] [bold blue]API Request:[/] Fetching page {data['page']} -> [dim]{data['url']}[/]")
    elif event_type == "quote_scraped":
        console.print(
            f"   [bold green]✔ QUOTE:[/] \"[white]{data['text']}[/]\" — [bold yellow]{data['author']}[/] "
            f"([dim]{data['tags_count']} tags[/])"
        )
    elif event_type == "author_enriched":
        console.print(
            f"     [bold purple]↳ ENRICHED AUTHOR BIO:[/] [white]{data['name']}[/] "
            f"born [cyan]{data['date']}[/] in [green]{data['location']}[/]"
        )


async def display_analytics(storage: AsyncRelationalStorage):
    """Runs relational SQL queries and renders analytics tables."""
    analytics = await storage.get_analytics()
    summary = analytics["summary"]

    # Summary Table
    summary_table = Table(title="Asynchronous Relational Database Metrics", show_header=True, header_style="bold cyan")
    summary_table.add_column("Entity", style="bold")
    summary_table.add_column("Count", style="green", justify="right")

    summary_table.add_row("Total Quotes Extracted", str(summary.get("total_quotes", 0)))
    summary_table.add_row("Total Unique Authors", str(summary.get("total_authors", 0)))
    summary_table.add_row("Total Unique Tags", str(summary.get("total_tags", 0)))
    console.print()
    console.print(summary_table)

    # Top Quoted Authors (SQL JOIN result)
    authors_table = Table(
        title="Top Quoted Authors (Enriched via Relational JOIN)",
        show_header=True,
        header_style="bold yellow"
    )
    authors_table.add_column("Author Name", style="bold white")
    authors_table.add_column("Birthplace (Scraped from Bio)", style="cyan")
    authors_table.add_column("Quotes Count", justify="right", style="green")

    for author in analytics["top_authors"]:
        authors_table.add_row(
            author["name"],
            author["born_location"] or "Unknown",
            str(author["quote_count"])
        )
    console.print(authors_table)

    # Top Tags Table
    tags_table = Table(title="Most Popular Tags", show_header=True, header_style="bold magenta")
    tags_table.add_column("Tag Name", style="bold")
    tags_table.add_column("Frequency", justify="right", style="yellow")

    for tag in analytics["top_tags"]:
        tags_table.add_row(f"#{tag['name']}", str(tag["count"]))
    console.print(tags_table)


async def async_main():
    parser = argparse.ArgumentParser(description="Project 2: Async Quotes & Dynamic API Crawler")
    parser.add_argument("--max-pages", type=int, default=3, help="Max API pages to crawl")
    parser.add_argument("--concurrency", type=int, default=5, help="Max concurrent HTTP connections")
    parser.add_argument("--db", default="data/quotes_relational.db", help="Path to relational SQLite DB")
    parser.add_argument("--no-enrich", action="store_true", help="Skip author biographical enrichment")

    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold magenta]Project 2: High-Concurrency Async & Network API Crawler[/bold magenta]\n"
        "[dim]Concepts: Asyncio Event Loops, Httpx, Semaphore Rate Limiting, JSON API Reverse-Engineering, 3NF SQLite[/dim]",
        border_style="magenta"
    ))

    storage = AsyncRelationalStorage(db_path=args.db)
    crawler = AsyncQuotesCrawler(
        max_pages=args.max_pages,
        max_concurrency=args.concurrency,
        enrich_authors=not args.no_enrich,
        storage=storage,
        on_event=handle_event,
    )

    stats = await crawler.run()

    console.print(f"\n[bold green]✔ Crawl Completed in {stats.elapsed_seconds}s![/]")
    console.print(
        f"Throughput: [bold yellow]{stats.quotes_per_second} quotes/sec[/] | "
        f"Authors Enriched: [bold cyan]{stats.authors_enriched}[/]"
    )

    await display_analytics(storage)


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
