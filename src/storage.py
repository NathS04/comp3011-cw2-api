"""JSON serialisation and deserialisation for the search index.

JSON was chosen over pickle or SQLite because:
- Human-readable — markers can open and inspect the index file.
- Portable and standard — no Python-version dependency.
- Sufficient for ~200 pages (~3-5 MB).
"""

from __future__ import annotations

import json
from pathlib import Path

from src.models import DocumentInfo, SearchIndex, TermEntry


def save_index(index: SearchIndex, path: str | Path) -> None:
    """Serialise *index* to a JSON file at *path*."""
    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, object] = {
        "metadata": index.metadata,
        "documents": {
            doc_id: doc.to_dict() for doc_id, doc in index.documents.items()
        },
        "terms": {
            term: entry.to_dict() for term, entry in index.terms.items()
        },
    }
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def load_index(path: str | Path) -> SearchIndex:
    """Deserialise a ``SearchIndex`` from the JSON file at *path*.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    json.JSONDecodeError
        If the file contains invalid JSON.
    """
    filepath = Path(path)
    with open(filepath, encoding="utf-8") as fh:
        raw = json.load(fh)

    documents: dict[str, DocumentInfo] = {
        doc_id: DocumentInfo.from_dict(doc_id, data)
        for doc_id, data in raw["documents"].items()
    }

    terms: dict[str, TermEntry] = {
        term: TermEntry.from_dict(data)
        for term, data in raw["terms"].items()
    }

    return SearchIndex(
        metadata=raw["metadata"],
        documents=documents,
        terms=terms,
    )
