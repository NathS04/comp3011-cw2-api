"""Regression and invariant tests for hardened submission quality.

Covers:
- /page/1 canonical collapsing for non-root paths
- No duplicate-equivalent URLs in index
- Deterministic result ordering on score ties
- print rejects multi-word input
- Retry backoff uses injected sleeper
- Index structural invariants (df, tf, positions)
- Repeated query returns identical results
- Save/load roundtrip preserves ordering and scores
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import requests

from src.crawler import BASE_URL, crawl, normalize_url
from src.indexer import build_index
from src.models import (
    CrawlResult,
    DocumentInfo,
    Posting,
    SearchIndex,
    TermEntry,
)
from src.search import _parse_query, find, print_term
from src.storage import load_index, save_index

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _fixture_pages() -> list[CrawlResult]:
    return [
        CrawlResult(
            url="http://test.com/page/1",
            title="Page 1",
            html_content=(FIXTURES_DIR / "page1.html").read_text("utf-8"),
            status_code=200,
        ),
        CrawlResult(
            url="http://test.com/page/2",
            title="Page 2",
            html_content=(FIXTURES_DIR / "page2.html").read_text("utf-8"),
            status_code=200,
        ),
        CrawlResult(
            url="http://test.com/author/Einstein",
            title="Author",
            html_content=(FIXTURES_DIR / "author.html").read_text("utf-8"),
            status_code=200,
        ),
    ]


def _fixture_index() -> SearchIndex:
    return build_index(_fixture_pages(), source_url="http://test.com")


# ── Canonical URL collapsing ─────────────────────────────────────────────


class TestCanonicalUrls:
    def test_tag_page1_equals_tag_base(self) -> None:
        assert normalize_url("/tag/friends/page/1") == normalize_url("/tag/friends")

    def test_tag_page1_trailing_slash(self) -> None:
        assert normalize_url("/tag/friends/page/1/") == normalize_url("/tag/friends")

    def test_author_page1_equals_author_base(self) -> None:
        assert normalize_url("/author/X/page/1") == normalize_url("/author/X")

    def test_root_page1_canonical(self) -> None:
        assert normalize_url("/") == normalize_url("/page/1")

    def test_tag_page2_not_collapsed(self) -> None:
        assert normalize_url("/tag/friends/page/2") != normalize_url("/tag/friends")

    def test_homepage_page2_not_collapsed(self) -> None:
        assert normalize_url("/page/2") != normalize_url("/page/1")


# ── No duplicate URLs in index ───────────────────────────────────────────


class TestNoDuplicateUrls:
    def test_no_page1_duplicate_in_fixture_index(self) -> None:
        index = _fixture_index()
        urls = [doc.url for doc in index.documents.values()]
        for url in urls:
            if url.endswith("/page/1"):
                base = url.rsplit("/page/1", 1)[0]
                assert base not in urls or base == ""


# ── Deterministic ordering ───────────────────────────────────────────────


class TestDeterministicOrdering:
    def test_equal_scores_sorted_by_url(self) -> None:
        docs = {
            "d1": DocumentInfo("d1", "http://x.com/b", "T", 10),
            "d2": DocumentInfo("d2", "http://x.com/a", "T", 10),
        }
        terms = {
            "hello": TermEntry(df=2, postings={
                "d1": Posting(tf=1, positions=[0], title_tf=0),
                "d2": Posting(tf=1, positions=[0], title_tf=0),
            }),
        }
        idx = SearchIndex(
            metadata={"num_documents": 2, "num_terms": 1},
            documents=docs,
            terms=terms,
        )
        results = find(idx, "hello")
        assert len(results) == 2
        assert results[0].url <= results[1].url

    def test_repeated_query_identical_order(self) -> None:
        index = _fixture_index()
        r1 = find(index, "einstein")
        r2 = find(index, "einstein")
        assert [r.doc_id for r in r1] == [r.doc_id for r in r2]
        assert [r.score for r in r1] == [r.score for r in r2]


# ── print_term contract ─────────────────────────────────────────────────


class TestPrintContract:
    def test_single_word_works(self) -> None:
        index = _fixture_index()
        output = print_term(index, "world")
        assert "world" in output
        assert "tf=" in output

    def test_multi_word_rejected(self) -> None:
        index = _fixture_index()
        output = print_term(index, "good friends")
        assert "one term only" in output.lower()

    def test_empty_rejected(self) -> None:
        index = _fixture_index()
        output = print_term(index, "")
        assert "no valid" in output.lower()


# ── Retry uses injected sleeper ──────────────────────────────────────────


class TestRetrySleep:
    def test_retry_backoff_uses_sleep_fn(self) -> None:
        session = MagicMock(spec=requests.Session)
        session.get.return_value = MagicMock(
            spec=requests.Response, status_code=500, text=""
        )
        session.headers = {}
        sleeper = MagicMock()

        crawl(BASE_URL, session=session, sleep_fn=sleeper)

        backoff_calls = [c for c in sleeper.call_args_list if c.args[0] > 6]
        assert len(backoff_calls) >= 1, "retry backoff should call sleep_fn with > 6s"

    def test_connection_error_retry_uses_sleep_fn(self) -> None:
        session = MagicMock(spec=requests.Session)
        session.get.side_effect = requests.exceptions.ConnectionError("refused")
        session.headers = {}
        sleeper = MagicMock()

        crawl(BASE_URL, session=session, sleep_fn=sleeper)

        backoff_calls = [c for c in sleeper.call_args_list if c.args[0] > 6]
        assert len(backoff_calls) >= 1


# ── Index structural invariants ──────────────────────────────────────────


class TestIndexInvariants:
    def test_df_equals_posting_count(self) -> None:
        index = _fixture_index()
        for term, entry in index.terms.items():
            assert entry.df == len(entry.postings), f"df mismatch for '{term}'"

    def test_tf_equals_position_count(self) -> None:
        index = _fixture_index()
        for term, entry in index.terms.items():
            for doc_id, posting in entry.postings.items():
                assert posting.tf == len(posting.positions), (
                    f"tf/positions mismatch for '{term}' in {doc_id}"
                )

    def test_positions_sorted(self) -> None:
        index = _fixture_index()
        for term, entry in index.terms.items():
            for doc_id, posting in entry.postings.items():
                assert posting.positions == sorted(posting.positions), (
                    f"positions not sorted for '{term}' in {doc_id}"
                )


# ── Title/body phrase boundary ───────────────────────────────────────────


class TestTitleBodyBoundary:
    """Phrase queries must not match across the title/body boundary."""

    def _index_with_title_body(self, title: str, body: str) -> SearchIndex:
        from src.indexer import build_index

        html = (
            f"<html><head><title>{title}</title></head>"
            f"<body><div class=\"quote\">"
            f"<span class=\"text\">{body}</span>"
            f"<small class=\"author\">x</small>"
            f"</div></body></html>"
        )
        page = CrawlResult(
            url="http://test.com/p",
            title=title,
            html_content=html,
            status_code=200,
        )
        return build_index([page])

    def test_phrase_does_not_cross_title_body_boundary(self) -> None:
        index = self._index_with_title_body("foo bar", "baz qux")
        results = find(index, '"bar baz"')
        assert results == [], (
            "Phrase 'bar baz' must not match across title/body boundary"
        )

    def test_phrase_within_title_still_matches(self) -> None:
        index = self._index_with_title_body("foo bar", "other content")
        results = find(index, '"foo bar"')
        assert len(results) == 1

    def test_phrase_within_body_still_matches(self) -> None:
        index = self._index_with_title_body("title", "alpha beta gamma")
        results = find(index, '"alpha beta"')
        assert len(results) == 1

    def test_unquoted_query_still_matches_across_fields(self) -> None:
        """Conjunctive AND should still match even if terms are split fields."""
        index = self._index_with_title_body("foo bar", "baz qux")
        results = find(index, "bar baz")
        assert len(results) == 1


# ── Quoted exact phrase search ───────────────────────────────────────────


class TestQuotedPhraseSearch:
    def test_parse_unquoted(self) -> None:
        tokens, exact = _parse_query("good friends")
        assert tokens == ["good", "friends"]
        assert exact is False

    def test_parse_quoted(self) -> None:
        tokens, exact = _parse_query('"good friends"')
        assert tokens == ["good", "friends"]
        assert exact is True

    def test_quoted_filters_non_adjacent(self) -> None:
        docs = {
            "d1": DocumentInfo("d1", "http://x/1", "T", 10),
            "d2": DocumentInfo("d2", "http://x/2", "T", 10),
        }
        terms = {
            "good": TermEntry(df=2, postings={
                "d1": Posting(tf=1, positions=[0], title_tf=0),
                "d2": Posting(tf=1, positions=[0], title_tf=0),
            }),
            "friends": TermEntry(df=2, postings={
                "d1": Posting(tf=1, positions=[1], title_tf=0),
                "d2": Posting(tf=1, positions=[5], title_tf=0),
            }),
        }
        idx = SearchIndex(
            metadata={"num_documents": 2, "num_terms": 2},
            documents=docs,
            terms=terms,
        )
        quoted = find(idx, '"good friends"')
        unquoted = find(idx, "good friends")
        assert len(quoted) == 1
        assert quoted[0].doc_id == "d1"
        assert len(unquoted) == 2

    def test_quoted_single_word_works(self) -> None:
        index = _fixture_index()
        results = find(index, '"world"')
        assert len(results) >= 1

    def test_empty_quotes(self) -> None:
        index = _fixture_index()
        results = find(index, '""')
        assert results == []


# ── Roundtrip preserves ordering and scores ──────────────────────────────


class TestRoundtripOrdering:
    def test_scores_within_tolerance(self, tmp_path: Path) -> None:
        index = _fixture_index()
        results_before = find(index, "einstein")

        out = tmp_path / "index.json"
        save_index(index, out)
        loaded = load_index(out)
        results_after = find(loaded, "einstein")

        assert len(results_before) == len(results_after)
        for r_b, r_a in zip(results_before, results_after, strict=True):
            assert r_b.doc_id == r_a.doc_id
            assert abs(r_b.score - r_a.score) < 1e-10

    def test_ordering_preserved_across_roundtrip(self, tmp_path: Path) -> None:
        index = _fixture_index()
        r1 = find(index, "the")

        out = tmp_path / "index.json"
        save_index(index, out)
        loaded = load_index(out)
        r2 = find(loaded, "the")

        assert [r.doc_id for r in r1] == [r.doc_id for r in r2]
