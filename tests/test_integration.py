"""End-to-end integration tests: build -> save -> load -> query.

These tests use the HTML fixture files (not the live network) so they
are deterministic and fast.
"""

from __future__ import annotations

from pathlib import Path

from src.indexer import build_index
from src.models import CrawlResult
from src.search import find, print_term
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


class TestFullPipeline:
    def test_build_from_fixtures(self) -> None:
        pages = _fixture_pages()
        index = build_index(pages, source_url="http://test.com")
        assert len(index.documents) == 3
        assert len(index.terms) > 0

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        pages = _fixture_pages()
        index = build_index(pages)
        out = tmp_path / "index.json"
        save_index(index, out)
        loaded = load_index(out)
        assert len(loaded.documents) == len(index.documents)
        assert len(loaded.terms) == len(index.terms)

    def test_full_pipeline_find_single(self, tmp_path: Path) -> None:
        pages = _fixture_pages()
        index = build_index(pages)
        out = tmp_path / "index.json"
        save_index(index, out)
        loaded = load_index(out)

        results = find(loaded, "world")
        assert len(results) >= 1
        urls = [r.url for r in results]
        assert any("page/1" in u for u in urls)

    def test_full_pipeline_find_multi_word(self, tmp_path: Path) -> None:
        pages = _fixture_pages()
        index = build_index(pages)
        out = tmp_path / "index.json"
        save_index(index, out)
        loaded = load_index(out)

        results = find(loaded, "albert einstein")
        assert len(results) >= 1

    def test_full_pipeline_print(self, tmp_path: Path) -> None:
        pages = _fixture_pages()
        index = build_index(pages)
        out = tmp_path / "index.json"
        save_index(index, out)
        loaded = load_index(out)

        output = print_term(loaded, "world")
        assert "world" in output
        assert "tf=" in output

    def test_full_pipeline_missing_term(self, tmp_path: Path) -> None:
        pages = _fixture_pages()
        index = build_index(pages)
        out = tmp_path / "index.json"
        save_index(index, out)
        loaded = load_index(out)

        results = find(loaded, "xyznonexistent")
        assert results == []

    def test_find_author_content(self, tmp_path: Path) -> None:
        """Verify that author-page text is searchable."""
        pages = _fixture_pages()
        index = build_index(pages)
        out = tmp_path / "index.json"
        save_index(index, out)
        loaded = load_index(out)

        results = find(loaded, "photoelectric")
        assert len(results) >= 1

    def test_ranking_consistency_after_roundtrip(self, tmp_path: Path) -> None:
        """Rankings are identical before and after save/load."""
        pages = _fixture_pages()
        index = build_index(pages)
        results_before = find(index, "einstein")

        out = tmp_path / "index.json"
        save_index(index, out)
        loaded = load_index(out)
        results_after = find(loaded, "einstein")

        scores_before = [r.score for r in results_before]
        scores_after = [r.score for r in results_after]
        assert scores_before == scores_after
