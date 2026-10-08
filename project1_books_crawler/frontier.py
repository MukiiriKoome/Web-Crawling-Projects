"""
URL Frontier and Politeness Engine.

Demonstrates:
- Breadth-First Search (BFS) Frontier with collections.deque.
- Visited Set deduplication to prevent infinite loops and cyclic crawls.
- URL Canonicalization (normalizing schemes, lowercase domains, removing anchors).
- Domain boundary restrictions (ensuring crawler does not escape target site).
- Robots.txt parser integration (urllib.robotparser).
- Politeness delay with randomized jitter.
"""

from collections import deque
import logging
import random
import time
from typing import Deque, Optional, Set, Tuple
from urllib.parse import urlparse, urldefrag
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)


class UrlFrontier:
    """
    Manages URLs to visit, enforcing politeness, deduplication, and domain scope.
    """

    def __init__(
        self,
        allowed_domains: Optional[Set[str]] = None,
        max_depth: int = 3,
        politeness_delay: float = 0.5,
        respect_robots: bool = True,
        user_agent: str = "*",
    ):
        self.queue: Deque[Tuple[str, int]] = deque()
        self.visited: Set[str] = set()
        self.allowed_domains: Set[str] = allowed_domains or set()
        self.max_depth = max_depth
        self.politeness_delay = politeness_delay
        self.respect_robots = respect_robots
        self.user_agent = user_agent
        self.robot_parsers: dict[str, RobotFileParser] = {}
        self.last_request_time: float = 0.0

    @staticmethod
    def canonicalize_url(url: str) -> str:
        """
        Normalizes a URL so that duplicate representations map to the identical string:
        - Drops URL fragments (#...)
        - Normalizes scheme and netloc to lowercase
        - Strips trailing slash on root paths
        """
        url, _ = urldefrag(url.strip())
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path or "/"
        
        # Keep query parameters if any
        query = f"?{parsed.query}" if parsed.query else ""
        return f"{scheme}://{netloc}{path}{query}"

    def init_robots(self, base_url: str):
        """
        Fetches and initializes robots.txt parsing for the root domain.
        """
        if not self.respect_robots:
            return

        parsed = urlparse(base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = f"{origin}/robots.txt"

        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
            self.robot_parsers[parsed.netloc] = rp
            logger.info(f"Loaded robots.txt from {robots_url}")
        except Exception as e:
            logger.warning(f"Could not load robots.txt from {robots_url}: {e} (proceeding cautiously)")

    def is_allowed_by_robots(self, url: str) -> bool:
        """Checks if URL path is allowed by parsed robots.txt."""
        if not self.respect_robots:
            return True
        netloc = urlparse(url).netloc.lower()
        rp = self.robot_parsers.get(netloc)
        if rp:
            return rp.can_fetch(self.user_agent, url)
        return True

    def is_allowed_domain(self, url: str) -> bool:
        """Checks if the URL's domain belongs to the target domain scope."""
        if not self.allowed_domains:
            return True
        domain = urlparse(url).netloc.lower()
        # Allow exact match or subdomain
        return any(domain == d or domain.endswith(f".{d}") for d in self.allowed_domains)

    def add_url(self, url: str, depth: int = 0) -> bool:
        """
        Validates, canonicalizes, and enqueues a URL if it has not been visited.
        Returns True if enqueued, False otherwise.
        """
        if depth > self.max_depth:
            return False

        canonical = self.canonicalize_url(url)

        if canonical in self.visited:
            return False

        if not self.is_allowed_domain(canonical):
            return False

        if not self.is_allowed_by_robots(canonical):
            logger.debug(f"Blocked by robots.txt: {canonical}")
            return False

        # Mark as visited when queued to prevent duplicate entries in queue
        self.visited.add(canonical)
        self.queue.append((canonical, depth))
        return True

    def get_next_url(self) -> Optional[Tuple[str, int]]:
        """
        Retrieves the next URL to crawl using BFS (First-In-First-Out).
        Applies politeness delay with jitter before returning.
        """
        if not self.queue:
            return None

        # Apply polite rate limiting with random jitter (e.g. ±20%)
        if self.politeness_delay > 0:
            elapsed = time.time() - self.last_request_time
            jitter = random.uniform(0.8, 1.2)
            target_delay = self.politeness_delay * jitter
            if elapsed < target_delay:
                time.sleep(target_delay - elapsed)

        self.last_request_time = time.time()
        return self.queue.popleft()

    def has_pending_urls(self) -> bool:
        """Checks if there are URLs remaining in the queue."""
        return len(self.queue) > 0

    @property
    def queue_size(self) -> int:
        return len(self.queue)

    @property
    def visited_count(self) -> int:
        return len(self.visited)
