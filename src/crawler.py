"""BFS web crawler with politeness window and retry logic.

Design decisions (justified from COMP3011 Lecture 9):
- Breadth-first traversal using a FIFO deque as the URL frontier.
- Visited set prevents duplicate fetches.
- URL normalisation deduplicates equivalent URLs (e.g. "/" and "/page/1/").
- An injectable sleep function allows tests to verify politeness without waiting.
- Retry with exponential back-off (3 attempts) for transient network errors.
- Only follows internal links within the target domain.
"""

from __future__ import annotations

import logging
import re
import time
from collections import deque
from collections.abc import Callable
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from src.models import CrawlResult

logger = logging.getLogger(__name__)

BASE_URL = "https://quotes.toscrape.com"
DEFAULT_POLITENESS_SECONDS = 6
MAX_RETRIES = 3
REQUEST_TIMEOUT = 10

# Paths that should not be crawled
_SKIP_PATHS = frozenset({"/login", "/logout", "/static"})


_PAGE1_SUFFIX_RE = re.compile(r"^(/(?:tag|author)/.+)/page/1$")


def normalize_url(url: str, base: str = BASE_URL) -> str | None:
    """Normalise *url* relative to *base* and return it, or ``None`` to skip.

    Rules:
    - Resolve relative URLs against *base*.
    - Strip fragments, query strings, and trailing slashes.
    - Reject external domains, login pages, and static assets.
    - Canonicalise ``/`` and ``/page/1`` to the same URL.
    - Canonicalise ``/tag/X/page/1`` to ``/tag/X`` (and likewise for author
      paths) so the first pagination page is never a duplicate of the base.
    """
    absolute = urljoin(base + "/", url)
    parsed = urlparse(absolute)

    if parsed.hostname and parsed.hostname not in (
        "quotes.toscrape.com",
        "www.quotes.toscrape.com",
    ):
        return None

    path = parsed.path.rstrip("/") or "/"

    for skip in _SKIP_PATHS:
        if path.startswith(skip):
            return None

    if path == "/":
        path = "/page/1"

    m = _PAGE1_SUFFIX_RE.match(path)
    if m:
        path = m.group(1)

    normalised = urlunparse((
        parsed.scheme or "https",
        parsed.netloc or urlparse(base).netloc,
        path,
        "",  # params
        "",  # query
        "",  # fragment
    ))
    return normalised


def extract_links(html: str, page_url: str) -> list[str]:
    """Return a list of normalised internal URLs found in *html*."""
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href: str = anchor["href"]
        normalised = normalize_url(href, page_url)
        if normalised is not None:
            links.append(normalised)
    return links


def _fetch_page(
    session: requests.Session,
    url: str,
    *,
    timeout: int = REQUEST_TIMEOUT,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> requests.Response | None:
    """Fetch *url* with up to ``MAX_RETRIES`` attempts on transient errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, timeout=timeout)
            if response.status_code >= 500:
                logger.warning(
                    "Server error %d for %s (attempt %d/%d)",
                    response.status_code,
                    url,
                    attempt,
                    MAX_RETRIES,
                )
                if attempt < MAX_RETRIES:
                    sleep_fn(DEFAULT_POLITENESS_SECONDS * attempt)
                    continue
                return None
            return response
        except requests.RequestException as exc:
            logger.warning(
                "Request failed for %s (attempt %d/%d): %s",
                url,
                attempt,
                MAX_RETRIES,
                exc,
            )
            if attempt < MAX_RETRIES:
                sleep_fn(DEFAULT_POLITENESS_SECONDS * attempt)
    return None


def crawl(
    seed_url: str = BASE_URL,
    *,
    session: requests.Session | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    politeness: float = DEFAULT_POLITENESS_SECONDS,
    on_page: Callable[[CrawlResult], None] | None = None,
) -> list[CrawlResult]:
    """Crawl the target site starting from *seed_url* using BFS.

    Parameters
    ----------
    seed_url:
        The starting URL.
    session:
        An injectable ``requests.Session`` (useful for mocking in tests).
    sleep_fn:
        Callable used to wait between requests.  Defaults to ``time.sleep``.
    politeness:
        Seconds to wait between successive HTTP requests.
    on_page:
        Optional callback invoked with each ``CrawlResult`` as it is fetched.

    Returns
    -------
    list[CrawlResult]
        All successfully crawled pages.
    """
    if session is None:
        session = requests.Session()
        session.headers.update({"User-Agent": "COMP3011-SearchBot/1.0"})

    start_normalised = normalize_url(seed_url, seed_url)
    if start_normalised is None:
        start_normalised = normalize_url("/", seed_url)
    if start_normalised is None:
        raise ValueError(
            f"seed_url {seed_url!r} cannot be normalised to a crawlable URL"
        )

    frontier: deque[str] = deque([start_normalised])
    enqueued: set[str] = {start_normalised}
    visited: set[str] = set()
    results: list[CrawlResult] = []
    is_first_request = True

    while frontier:
        url = frontier.popleft()
        if url in visited:
            continue
        visited.add(url)

        if not is_first_request:
            sleep_fn(politeness)
        is_first_request = False

        response = _fetch_page(session, url, sleep_fn=sleep_fn)
        if response is None:
            logger.info("Skipping %s after failed retries", url)
            continue

        if response.status_code == 404:
            logger.debug("404 for %s — skipping", url)
            continue

        if response.status_code >= 400:
            logger.info("HTTP %d for %s — skipping", response.status_code, url)
            continue

        html = response.text
        title_tag = BeautifulSoup(html, "html.parser").find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        result = CrawlResult(
            url=url,
            title=title,
            html_content=html,
            status_code=response.status_code,
        )
        results.append(result)
        if on_page:
            on_page(result)

        for link in extract_links(html, url):
            if link not in enqueued:
                enqueued.add(link)
                frontier.append(link)

        logger.info("Crawled %s (%d pages so far)", url, len(results))

    return results
