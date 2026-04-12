"""Data models for the search engine tool.

All shared dataclasses live here so every other module imports from one place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class CrawlResult:
    """A single page returned by the crawler."""

    url: str
    title: str
    html_content: str
    status_code: int
    crawled_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class DocumentInfo:
    """Metadata about an indexed document."""

    doc_id: str
    url: str
    title: str
    word_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "word_count": self.word_count,
        }

    @classmethod
    def from_dict(cls, doc_id: str, data: dict[str, Any]) -> DocumentInfo:
        return cls(
            doc_id=doc_id,
            url=str(data["url"]),
            title=str(data["title"]),
            word_count=int(data["word_count"]),
        )


@dataclass
class Posting:
    """Statistics for one term in one document."""

    tf: int
    positions: list[int]
    title_tf: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tf": self.tf,
            "positions": self.positions,
            "title_tf": self.title_tf,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Posting:
        return cls(
            tf=int(data["tf"]),
            positions=[int(p) for p in data["positions"]],
            title_tf=int(data.get("title_tf", 0)),
        )


@dataclass
class TermEntry:
    """Inverted-index entry for a single term."""

    df: int
    postings: dict[str, Posting]

    def to_dict(self) -> dict[str, Any]:
        return {
            "df": self.df,
            "postings": {doc_id: p.to_dict() for doc_id, p in self.postings.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TermEntry:
        raw_postings: dict[str, Any] = data.get("postings", {})
        return cls(
            df=int(data["df"]),
            postings={
                doc_id: Posting.from_dict(pdata) for doc_id, pdata in raw_postings.items()
            },
        )


@dataclass
class SearchIndex:
    """The complete inverted index with metadata and document registry."""

    metadata: dict[str, Any]
    documents: dict[str, DocumentInfo]
    terms: dict[str, TermEntry]
