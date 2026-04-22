"""Tests for the inverted-index builder."""

from __future__ import annotations

from pathlib import Path

from src.indexer import build_index
from src.models import CrawlResult

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def _make_page(html_file: str, url: str = "http://test.com") -> CrawlResult:
    return CrawlResult(
        url=url,
        title="Test",
        html_content=_load_fixture(html_file),
        status_code=200,
    )


class TestBuildIndex:
    def test_single_document(self) -> None:
        pages = [_make_page("page1.html", "http://test.com/page/1")]
        index = build_index(pages)
        assert len(index.documents) == 1
        assert "doc_0000" in index.documents

    def test_multiple_documents(self) -> None:
        pages = [
            _make_page("page1.html", "http://test.com/page/1"),
            _make_page("page2.html", "http://test.com/page/2"),
        ]
        index = build_index(pages)
        assert len(index.documents) == 2

    def test_term_frequency_correct(self) -> None:
        pages = [_make_page("page1.html")]
        index = build_index(pages)
        # "world" appears in the quote text and as a tag
        assert "world" in index.terms
        posting = index.terms["world"].postings["doc_0000"]
        assert posting.tf >= 1

    def test_positions_are_integers(self) -> None:
        pages = [_make_page("page1.html")]
        index = build_index(pages)
        for term_entry in index.terms.values():
            for posting in term_entry.postings.values():
                assert all(isinstance(p, int) for p in posting.positions)

    def test_positions_match_tf(self) -> None:
        pages = [_make_page("page1.html")]
        index = build_index(pages)
        for term_entry in index.terms.values():
            for posting in term_entry.postings.values():
                assert len(posting.positions) == posting.tf

    def test_document_frequency(self) -> None:
        pages = [
            _make_page("page1.html", "http://test.com/1"),
            _make_page("page2.html", "http://test.com/2"),
        ]
        index = build_index(pages)
        # Both pages likely contain common terms from their titles
        for term_entry in index.terms.values():
            assert term_entry.df == len(term_entry.postings)

    def test_title_tf_recorded(self) -> None:
        pages = [_make_page("page1.html")]
        index = build_index(pages)
        # "quotes" appears in the title "Quotes to Scrape"
        assert "quotes" in index.terms
        posting = index.terms["quotes"].postings["doc_0000"]
        assert posting.title_tf >= 1

    def test_word_count_positive(self) -> None:
        pages = [_make_page("page1.html")]
        index = build_index(pages)
        doc = index.documents["doc_0000"]
        assert doc.word_count > 0

    def test_case_insensitive(self) -> None:
        pages = [_make_page("page1.html")]
        index = build_index(pages)
        assert "albert" in index.terms
        assert "Albert" not in index.terms

    def test_document_url_stored(self) -> None:
        pages = [_make_page("page1.html", "http://test.com/page/1")]
        index = build_index(pages)
        assert index.documents["doc_0000"].url == "http://test.com/page/1"

    def test_metadata_populated(self) -> None:
        pages = [_make_page("page1.html")]
        index = build_index(pages)
        assert index.metadata["num_documents"] == 1
        assert index.metadata["num_terms"] == len(index.terms)
        assert "created_at" in index.metadata

    def test_author_page_indexed(self) -> None:
        pages = [_make_page("author.html", "http://test.com/author/Einstein")]
        index = build_index(pages)
        assert "einstein" in index.terms
        assert "photoelectric" in index.terms

    def test_empty_pages_list(self) -> None:
        index = build_index([])
        assert len(index.documents) == 0
        assert len(index.terms) == 0

    def test_index_preserves_all_terms(self) -> None:
        pages = [_make_page("page1.html")]
        index = build_index(pages)
        assert "thinking" in index.terms
        assert "change" in index.terms
        assert "abilities" in index.terms
