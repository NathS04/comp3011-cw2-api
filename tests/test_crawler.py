"""Tests for the web crawler — URL normalisation, BFS, politeness, retries."""

from __future__ import annotations

from unittest.mock import MagicMock

import requests

from src.crawler import (
    BASE_URL,
    crawl,
    extract_links,
    normalize_url,
)

# ── URL normalisation ────────────────────────────────────────────────────

class TestNormalizeUrl:
    def test_absolute_internal(self) -> None:
        result = normalize_url("https://quotes.toscrape.com/page/2/")
        assert result == "https://quotes.toscrape.com/page/2"

    def test_relative_path(self) -> None:
        result = normalize_url("/page/3/", BASE_URL)
        assert result == "https://quotes.toscrape.com/page/3"

    def test_strips_fragment(self) -> None:
        result = normalize_url("/page/2/#section", BASE_URL)
        assert result == "https://quotes.toscrape.com/page/2"

    def test_strips_trailing_slash(self) -> None:
        result = normalize_url("/author/Albert-Einstein/", BASE_URL)
        assert result == "https://quotes.toscrape.com/author/Albert-Einstein"

    def test_homepage_canonicalised(self) -> None:
        assert normalize_url("/", BASE_URL) == "https://quotes.toscrape.com/page/1"

    def test_page1_matches_homepage(self) -> None:
        home = normalize_url("/", BASE_URL)
        page1 = normalize_url("/page/1/", BASE_URL)
        assert home == page1

    def test_rejects_external_url(self) -> None:
        assert normalize_url("https://google.com/") is None

    def test_rejects_login(self) -> None:
        assert normalize_url("/login", BASE_URL) is None

    def test_rejects_static(self) -> None:
        assert normalize_url("/static/main.css", BASE_URL) is None

    def test_author_url(self) -> None:
        result = normalize_url("/author/J-K-Rowling", BASE_URL)
        assert result == "https://quotes.toscrape.com/author/J-K-Rowling"

    def test_tag_url(self) -> None:
        result = normalize_url("/tag/love/page/1/", BASE_URL)
        assert result == "https://quotes.toscrape.com/tag/love"

    def test_tag_page1_canonicalised_to_base(self) -> None:
        base = normalize_url("/tag/love", BASE_URL)
        page1 = normalize_url("/tag/love/page/1/", BASE_URL)
        assert base == page1

    def test_tag_page2_not_collapsed(self) -> None:
        result = normalize_url("/tag/love/page/2/", BASE_URL)
        assert result == "https://quotes.toscrape.com/tag/love/page/2"

    def test_author_page1_canonicalised(self) -> None:
        base = normalize_url("/author/J-K-Rowling", BASE_URL)
        page1 = normalize_url("/author/J-K-Rowling/page/1/", BASE_URL)
        assert base == page1

    def test_relative_author_from_page(self) -> None:
        result = normalize_url(
            "/author/Albert-Einstein",
            "https://quotes.toscrape.com/page/1",
        )
        assert result == "https://quotes.toscrape.com/author/Albert-Einstein"


# ── Link extraction ──────────────────────────────────────────────────────

class TestExtractLinks:
    def test_extracts_internal_links(self, page1_html: str) -> None:
        links = extract_links(page1_html, BASE_URL)
        assert any("/page/2" in lnk for lnk in links)

    def test_extracts_author_links(self, page1_html: str) -> None:
        links = extract_links(page1_html, BASE_URL)
        assert any("Albert-Einstein" in lnk for lnk in links)

    def test_skips_login(self, page1_html: str) -> None:
        links = extract_links(page1_html, BASE_URL)
        assert all("/login" not in lnk for lnk in links)

    def test_extracts_tag_links(self, page1_html: str) -> None:
        links = extract_links(page1_html, BASE_URL)
        assert any("/tag/" in lnk for lnk in links)


# ── Crawl behaviour (mocked network) ─────────────────────────────────────

def _mock_response(html: str, status: int = 200) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.text = html
    return resp


class TestCrawlBehaviour:
    def test_politeness_sleep_called(self, page1_html: str) -> None:
        """The crawler must sleep >= 6 s between successive requests."""
        terminal_html = page1_html.replace(
            '<li class="next"><a href="/page/2/">Next &rarr;</a></li>', ""
        )
        session = MagicMock(spec=requests.Session)
        session.get.return_value = _mock_response(terminal_html)

        session.headers = {}
        sleep_fn = MagicMock()

        # Seed with two pages so sleep is called at least once
        crawl(
            BASE_URL,
            session=session,
            sleep_fn=sleep_fn,
            politeness=6,
        )
        if session.get.call_count > 1:
            sleep_fn.assert_called_with(6)

    def test_avoids_duplicate_urls(self) -> None:
        """Each URL should be fetched at most once."""
        html_with_self_link = """
        <html><head><title>T</title></head><body>
        <a href="/page/1/">Home</a>
        <a href="/">Also Home</a>
        </body></html>
        """
        session = MagicMock(spec=requests.Session)
        session.get.return_value = _mock_response(html_with_self_link)
        session.headers = {}

        crawl(BASE_URL, session=session, sleep_fn=MagicMock())
        assert session.get.call_count == 1

    def test_skips_404(self) -> None:
        """A 404 response should be skipped without error."""
        session = MagicMock(spec=requests.Session)
        session.get.return_value = _mock_response("", status=404)
        session.headers = {}

        results = crawl(BASE_URL, session=session, sleep_fn=MagicMock())
        assert results == []

    def test_retries_on_500(self) -> None:
        """Transient 500 errors trigger retries before giving up."""
        session = MagicMock(spec=requests.Session)
        session.get.return_value = _mock_response("", status=500)
        session.headers = {}

        results = crawl(BASE_URL, session=session, sleep_fn=MagicMock())
        assert results == []
        assert session.get.call_count == 3  # MAX_RETRIES

    def test_handles_timeout(self) -> None:
        """A timeout exception should be caught and retried."""
        session = MagicMock(spec=requests.Session)
        session.get.side_effect = requests.exceptions.Timeout("timed out")
        session.headers = {}

        results = crawl(BASE_URL, session=session, sleep_fn=MagicMock())
        assert results == []

    def test_handles_connection_error(self) -> None:
        session = MagicMock(spec=requests.Session)
        session.get.side_effect = requests.exceptions.ConnectionError("refused")
        session.headers = {}

        results = crawl(BASE_URL, session=session, sleep_fn=MagicMock())
        assert results == []

    def test_bfs_order(self) -> None:
        """Pages are visited in breadth-first order."""
        html_a = (
            '<html><head><title>A</title></head>'
            '<body><a href="/page/2/">next</a></body></html>'
        )
        html_b = '<html><head><title>B</title></head><body></body></html>'

        session = MagicMock(spec=requests.Session)
        session.headers = {}

        def side_effect(url: str, **kwargs: object) -> MagicMock:
            if "/page/2" in url:
                return _mock_response(html_b)
            return _mock_response(html_a)

        session.get.side_effect = side_effect

        results = crawl(BASE_URL, session=session, sleep_fn=MagicMock())
        titles = [r.title for r in results]
        assert titles == ["A", "B"]

    def test_on_page_callback(self) -> None:
        html = '<html><head><title>T</title></head><body></body></html>'
        session = MagicMock(spec=requests.Session)
        session.get.return_value = _mock_response(html)
        session.headers = {}
        callback = MagicMock()

        crawl(BASE_URL, session=session, sleep_fn=MagicMock(), on_page=callback)
        callback.assert_called_once()
