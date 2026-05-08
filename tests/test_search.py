"""Tests for the query engine — print, find, ranking, phrase boost, suggestions."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.indexer import build_index
from src.models import (
    CrawlResult,
    DocumentInfo,
    Posting,
    SearchIndex,
    TermEntry,
)
from src.search import (
    SearchResult,
    _has_exact_phrase,
    _tfidf_score,
    find,
    get_suggestions,
    intersect_postings,
    print_term,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _fixture_index() -> SearchIndex:
    pages = [
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
    return build_index(pages, source_url="http://test.com")


@pytest.fixture()
def index() -> SearchIndex:
    return _fixture_index()


# ── Posting-list intersection ─────────────────────────────────────────────

class TestIntersectPostings:
    def test_single_term(self, index: SearchIndex) -> None:
        result = intersect_postings(index, ["world"])
        assert len(result) >= 1

    def test_multi_term_and(self, index: SearchIndex) -> None:
        result = intersect_postings(index, ["albert", "einstein"])
        assert len(result) >= 1

    def test_missing_term_returns_empty(self, index: SearchIndex) -> None:
        result = intersect_postings(index, ["xyznonexistent"])
        assert result == set()

    def test_empty_terms_returns_empty(self, index: SearchIndex) -> None:
        result = intersect_postings(index, [])
        assert result == set()

    def test_partial_overlap(self, index: SearchIndex) -> None:
        result = intersect_postings(index, ["world", "xyznonexistent"])
        assert result == set()


# ── TF-IDF scoring ───────────────────────────────────────────────────────

class TestTfidfScore:
    def test_score_positive_for_matching_term(self, index: SearchIndex) -> None:
        doc_ids = intersect_postings(index, ["world"])
        for doc_id in doc_ids:
            score = _tfidf_score(index, doc_id, ["world"])
            assert score > 0

    def test_score_zero_for_missing_term(self, index: SearchIndex) -> None:
        score = _tfidf_score(index, "doc_0000", ["xyznonexistent"])
        assert score == 0.0

    def test_title_boost_increases_score(self) -> None:
        docs = {
            "d1": DocumentInfo("d1", "http://x/1", "Title", 10),
            "d2": DocumentInfo("d2", "http://x/2", "Other", 10),
            "d3": DocumentInfo("d3", "http://x/3", "Extra", 10),
        }
        terms = {
            "hello": TermEntry(df=2, postings={
                "d1": Posting(tf=1, positions=[0], title_tf=1),
                "d2": Posting(tf=1, positions=[0], title_tf=0),
            }),
        }
        idx = SearchIndex(
            metadata={"num_documents": 3, "num_terms": 1},
            documents=docs,
            terms=terms,
        )
        score_with_title = _tfidf_score(idx, "d1", ["hello"])
        score_without_title = _tfidf_score(idx, "d2", ["hello"])
        assert score_with_title > score_without_title


# ── Exact phrase detection ────────────────────────────────────────────────

class TestExactPhrase:
    def test_adjacent_positions(self) -> None:
        docs = {"d1": DocumentInfo("d1", "http://x/1", "T", 5)}
        terms = {
            "good": TermEntry(df=1, postings={
                "d1": Posting(tf=1, positions=[0], title_tf=0),
            }),
            "friends": TermEntry(df=1, postings={
                "d1": Posting(tf=1, positions=[1], title_tf=0),
            }),
        }
        idx = SearchIndex(metadata={}, documents=docs, terms=terms)
        assert _has_exact_phrase(idx, "d1", ["good", "friends"]) is True

    def test_non_adjacent_positions(self) -> None:
        docs = {"d1": DocumentInfo("d1", "http://x/1", "T", 5)}
        terms = {
            "good": TermEntry(df=1, postings={
                "d1": Posting(tf=1, positions=[0], title_tf=0),
            }),
            "friends": TermEntry(df=1, postings={
                "d1": Posting(tf=1, positions=[5], title_tf=0),
            }),
        }
        idx = SearchIndex(metadata={}, documents=docs, terms=terms)
        assert _has_exact_phrase(idx, "d1", ["good", "friends"]) is False

    def test_single_word_no_phrase(self) -> None:
        docs = {"d1": DocumentInfo("d1", "http://x/1", "T", 5)}
        terms = {
            "hello": TermEntry(df=1, postings={
                "d1": Posting(tf=1, positions=[0], title_tf=0),
            }),
        }
        idx = SearchIndex(metadata={}, documents=docs, terms=terms)
        assert _has_exact_phrase(idx, "d1", ["hello"]) is False


# ── find() end-to-end ─────────────────────────────────────────────────────

class TestFind:
    def test_find_single_word(self, index: SearchIndex) -> None:
        results = find(index, "world")
        assert len(results) >= 1
        assert all(isinstance(r, SearchResult) for r in results)

    def test_find_multi_word(self, index: SearchIndex) -> None:
        results = find(index, "albert einstein")
        assert len(results) >= 1

    def test_find_missing_term(self, index: SearchIndex) -> None:
        results = find(index, "xyznonexistent")
        assert results == []

    def test_find_empty_query(self, index: SearchIndex) -> None:
        results = find(index, "")
        assert results == []

    def test_find_punctuation_only(self, index: SearchIndex) -> None:
        results = find(index, "!!! ???")
        assert results == []

    def test_find_case_insensitive(self, index: SearchIndex) -> None:
        lower = find(index, "world")
        upper = find(index, "WORLD")
        assert len(lower) == len(upper)

    def test_find_results_sorted_by_score(self, index: SearchIndex) -> None:
        results = find(index, "einstein")
        if len(results) > 1:
            scores = [r.score for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_find_repeated_terms(self, index: SearchIndex) -> None:
        results_single = find(index, "world")
        results_repeated = find(index, "world world")
        assert len(results_single) == len(results_repeated)

    def test_find_numbers(self, index: SearchIndex) -> None:
        results = find(index, "1879")
        assert len(results) >= 1


# ── print_term() ──────────────────────────────────────────────────────────

class TestPrintTerm:
    def test_existing_term(self, index: SearchIndex) -> None:
        output = print_term(index, "world")
        assert "world" in output
        assert "tf=" in output

    def test_missing_term(self, index: SearchIndex) -> None:
        output = print_term(index, "xyznonexistent")
        assert "not found" in output.lower()

    def test_missing_term_with_close_match_offers_suggestion(
        self, index: SearchIndex
    ) -> None:
        """A near-miss should print a 'Did you mean' line."""
        output = print_term(index, "worls")  # one letter off 'world'
        assert "did you mean" in output.lower()
        assert "world" in output.lower()

    def test_empty_input(self, index: SearchIndex) -> None:
        output = print_term(index, "")
        assert "no valid" in output.lower()

    def test_case_insensitive(self, index: SearchIndex) -> None:
        output = print_term(index, "WORLD")
        assert "world" in output


class TestEdgeCases:
    def test_tfidf_score_with_empty_index(self) -> None:
        empty = SearchIndex(metadata={}, documents={}, terms={})
        score = _tfidf_score(empty, "doc_0000", ["anything"])
        assert score == 0.0

    def test_intersect_with_empty_index(self) -> None:
        empty = SearchIndex(metadata={}, documents={}, terms={})
        assert intersect_postings(empty, ["x", "y"]) == set()


# ── Query suggestions ────────────────────────────────────────────────────

class TestGetSuggestions:
    def test_close_match(self, index: SearchIndex) -> None:
        suggestions = get_suggestions(index, "worls")
        assert "world" in suggestions

    def test_no_match(self, index: SearchIndex) -> None:
        suggestions = get_suggestions(index, "zzzzzzzzzzz")
        assert suggestions == []

    def test_exact_match_included(self, index: SearchIndex) -> None:
        suggestions = get_suggestions(index, "world")
        assert "world" in suggestions
