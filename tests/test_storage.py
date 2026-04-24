"""Tests for index JSON serialisation and deserialisation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.indexer import build_index
from src.models import CrawlResult, DocumentInfo, Posting, SearchIndex, TermEntry
from src.storage import load_index, save_index

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _small_index() -> SearchIndex:
    """Build a small index from the test fixtures."""
    page1 = CrawlResult(
        url="http://test.com/page/1",
        title="Test",
        html_content=(FIXTURES_DIR / "page1.html").read_text(encoding="utf-8"),
        status_code=200,
    )
    return build_index([page1], source_url="http://test.com")


class TestSaveIndex:
    def test_save_creates_file(self, tmp_path: Path) -> None:
        index = _small_index()
        out = tmp_path / "index.json"
        save_index(index, out)
        assert out.exists()

    def test_save_produces_valid_json(self, tmp_path: Path) -> None:
        index = _small_index()
        out = tmp_path / "index.json"
        save_index(index, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "metadata" in data
        assert "documents" in data
        assert "terms" in data

    def test_save_overwrites_existing(self, tmp_path: Path) -> None:
        out = tmp_path / "index.json"
        out.write_text("old data")
        save_index(_small_index(), out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "metadata" in data

    def test_metadata_included(self, tmp_path: Path) -> None:
        index = _small_index()
        out = tmp_path / "index.json"
        save_index(index, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["metadata"]["num_documents"] == 1
        assert "created_at" in data["metadata"]


class TestLoadIndex:
    def test_load_returns_correct_structure(self, tmp_path: Path) -> None:
        index = _small_index()
        out = tmp_path / "index.json"
        save_index(index, out)
        loaded = load_index(out)
        assert isinstance(loaded, SearchIndex)
        assert len(loaded.documents) == len(index.documents)
        assert len(loaded.terms) == len(index.terms)

    def test_roundtrip_consistency(self, tmp_path: Path) -> None:
        index = _small_index()
        out = tmp_path / "index.json"
        save_index(index, out)
        loaded = load_index(out)

        for doc_id, doc in index.documents.items():
            loaded_doc = loaded.documents[doc_id]
            assert loaded_doc.url == doc.url
            assert loaded_doc.title == doc.title
            assert loaded_doc.word_count == doc.word_count

        for term, entry in index.terms.items():
            loaded_entry = loaded.terms[term]
            assert loaded_entry.df == entry.df
            for doc_id, posting in entry.postings.items():
                loaded_posting = loaded_entry.postings[doc_id]
                assert loaded_posting.tf == posting.tf
                assert loaded_posting.positions == posting.positions
                assert loaded_posting.title_tf == posting.title_tf

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_index(tmp_path / "nonexistent.json")

    def test_load_corrupt_json_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json!!!")
        with pytest.raises(json.JSONDecodeError):
            load_index(bad)

    def test_large_index_roundtrip(self, tmp_path: Path) -> None:
        """Synthetic 500-term index survives a save/load cycle."""
        docs = {
            "doc_0000": DocumentInfo("doc_0000", "http://x.com/1", "Title", 100),
        }
        terms: dict[str, TermEntry] = {}
        for i in range(500):
            word = f"word{i}"
            terms[word] = TermEntry(
                df=1,
                postings={
                    "doc_0000": Posting(tf=i + 1, positions=list(range(i + 1))),
                },
            )
        index = SearchIndex(
            metadata={"num_documents": 1, "num_terms": 500, "version": "1.0"},
            documents=docs,
            terms=terms,
        )
        out = tmp_path / "big.json"
        save_index(index, out)
        loaded = load_index(out)
        assert len(loaded.terms) == 500
        assert loaded.terms["word499"].postings["doc_0000"].tf == 500
