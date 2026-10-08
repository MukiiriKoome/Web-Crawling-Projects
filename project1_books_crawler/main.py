"""
Command-Line Interface (CLI) for Project 1: Books Crawler.

Demonstrates:
- Argument parsing with argparse.
- Terminal UI rendering with rich (tables, styling, status indicators).
- Real-time logging of scraping events.
"""

import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Support running directly or as a module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from project1_books_crawler.crawler import BooksCrawler
from project1_books_crawler.storage import StoragePipeline

console = Console()


def handle_event(event_type: str, data: dict):
    """Callback to render crawler activity onto the terminal."""
    if event_type == "crawl_started":
        console.print(f"[bold cyan]▶ Starting Crawl[/] on [yellow]{data['start_url']}[/] (Max pages: {data['max_pages']})")
    elif event_type == "fetching":
        console.print(
            f" [cyan]•[/] [[green]Page {data['visited']}/{data['max_pages']}[/]] "
            f"Depth {data['depth']} | Queue: {data['queue_size']} | [dim]{data['url'][:75]}...[/]"
        )
    elif event_type == "item_scraped":
        stars = "★" * data['rating'] + "☆" * (5 - data['rating'])
        console.print(
            f"   [bold green]✔ SCRAPED BOOK:[/] [bold white]{data['title'][:40]}[/] | "
            f"[yellow]£{data['price']:.2f}[/] | [magenta]{data['category']}[/] | [gold1]{stars}[/]"
        )
    elif event_type == "error":
        console.print(f"   [bold red]✖ ERROR:[/] {data['url']} - {data['error']}")
    elif event_type == "links_discovered":
        if data['enqueued_count'] > 0:
            console.print(f"   [dim]↳ Found {data['discovered_count']} links ({data['enqueued_count']} newly enqueued)[/dim]")


def display_results(storage: StoragePipeline):
    """Renders formatted tables showing the database contents and aggregations."""
    summary = storage.get_summary()

    # Overview Table
    summary_table = Table(title="Crawling Results & Data Analytics", show_header=True, header_style="bold cyan")
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Total Books Stored", str(summary.get("total_books", 0)))
    summary_table.add_row("Unique Categories", str(summary.get("total_categories", 0)))
    summary_table.add_row("Average Book Price", f"£{summary.get('avg_price', 0):.2f}")
    summary_table.add_row("Price Range", f"£{summary.get('min_price', 0):.2f} - £{summary.get('max_price', 0):.2f}")
    summary_table.add_row("Average Star Rating", f"{summary.get('avg_rating', 0):.1f} / 5.0")

    console.print()
    console.print(summary_table)

    # Top Categories Table
    cat_table = Table(title="Top Categories Scraped", show_header=True, header_style="bold magenta")
    cat_table.add_column("Category", style="bold")
    cat_table.add_column("Book Count", justify="right")
    cat_table.add_column("Avg Price", justify="right", style="yellow")

    for cat in summary.get("top_categories", []):
        cat_table.add_row(cat["category"], str(cat["count"]), f"£{cat['avg_price']:.2f}")

    if summary.get("top_categories"):
        console.print(cat_table)

    # Recent Books Sample
    recent = storage.get_recent_items(limit=5)
    if recent:
        items_table = Table(title="Sample Scraped Items (Latest 5)", show_header=True, header_style="bold blue")
        items_table.add_column("Title", style="white")
        items_table.add_column("Category", style="magenta")
        items_table.add_column("Price", justify="right", style="yellow")
        items_table.add_column("Rating", justify="center", style="gold1")
        items_table.add_column("Stock", style="dim")

        for item in recent:
            stars = "★" * item["rating"] + "☆" * (5 - item["rating"])
            items_table.add_row(
                item["title"][:35],
                item["category"],
                f"£{item['price']:.2f}",
                stars,
                item["availability"]
            )
        console.print(items_table)


def main():
    parser = argparse.ArgumentParser(description="Project 1: Polite Recursive Books Crawler")
    parser.add_argument("--start-url", default="https://books.toscrape.com/", help="Initial seed URL")
    parser.add_argument("--max-pages", type=int, default=10, help="Maximum number of pages to fetch")
    parser.add_argument("--max-depth", type=int, default=2, help="Maximum crawl depth from root")
    parser.add_argument("--delay", type=float, default=0.3, help="Politeness delay in seconds")
    parser.add_argument("--db", default="data/books.db", help="Path to SQLite database")
    parser.add_argument("--jsonl", default="data/books.jsonl", help="Path to JSON Lines output")
    parser.add_argument("--no-robots", action="store_true", help="Bypass robots.txt checking")

    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold cyan]Project 1: Polite Recursive Web Crawler[/bold cyan]\n"
        "[dim]Concepts: BFS Frontier, Visited Set, Robots.txt, Beautiful Soup, SQLite & JSONL Pipeline[/dim]",
        border_style="cyan"
    ))

    storage = StoragePipeline(db_path=args.db, jsonl_path=args.jsonl)
    crawler = BooksCrawler(
        start_url=args.start_url,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        delay=args.delay,
        respect_robots=not args.no_robots,
        storage=storage,
        on_event=handle_event,
    )

    stats = crawler.run()
    console.print(f"\n[bold green]✔ Crawl Finished in {stats.duration_seconds}s![/]")
    console.print(f"Pages visited: [bold]{stats.pages_visited}[/], Items saved: [bold]{stats.items_scraped}[/]")
    display_results(storage)


if __name__ == "__main__":
    main()
