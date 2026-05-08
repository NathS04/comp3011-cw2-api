"""Inverted-index builder.

Constructs a ``SearchIndex`` from a list of ``CrawlResult`` objects.
Each document's title and body are tokenised separately so that
title-term-frequency (``title_tf``) can be recorded alongside overall
term frequency (``tf``) and word positions.

Title and body tokens are placed in a single position stream separated
by ``FIELD_GAP`` empty positions so that exact-phrase queries cannot
match across the title/body boundary. Within-title and within-body
phrase matches are unaffected.

The index design is based on the inverted-index structures covered in
COMP3011 Lecture 12 (Indexing), storing tf, positions, and field
information per posting.
"""

from __future__ import annotations

from datetime import UTC, datetime

from src.models import CrawlResult, DocumentInfo, Posting, SearchIndex, TermEntry
from src.tokenizer import extract_page_text, tokenize

# Gap inserted between title and body position streams. Must exceed the
# longest plausible phrase query so adjacency checks cannot bridge fields.
FIELD_GAP = 100


def _make_doc_id(index: int) -> str:
    """Generate a zero-padded document identifier."""
    return f"doc_{index:04d}"


def build_index(pages: list[CrawlResult], source_url: str = "") -> SearchIndex:
    """Build an inverted index from *pages*.

    Parameters
    ----------
    pages:
        Crawled page results to index.
    source_url:
        The root URL of the crawled site (stored in metadata).

    Returns
    -------
    SearchIndex
        The complete in-memory index ready for querying or serialisation.
    """
    documents: dict[str, DocumentInfo] = {}
    terms: dict[str, TermEntry] = {}

    for idx, page in enumerate(pages):
        doc_id = _make_doc_id(idx)
        title_text, body_text = extract_page_text(page.html_content)

        title_tokens = tokenize(title_text)
        body_tokens = tokenize(body_text)

        documents[doc_id] = DocumentInfo(
            doc_id=doc_id,
            url=page.url,
            title=title_text or page.title,
            word_count=len(title_tokens) + len(body_tokens),
        )

        title_freq: dict[str, int] = {}
        token_positions: dict[str, list[int]] = {}
        token_freq: dict[str, int] = {}

        for pos, token in enumerate(title_tokens):
            title_freq[token] = title_freq.get(token, 0) + 1
            token_freq[token] = token_freq.get(token, 0) + 1
            token_positions.setdefault(token, []).append(pos)

        body_start = len(title_tokens) + FIELD_GAP
        for offset, token in enumerate(body_tokens):
            pos = body_start + offset
            token_freq[token] = token_freq.get(token, 0) + 1
            token_positions.setdefault(token, []).append(pos)

        for token, tf in token_freq.items():
            posting = Posting(
                tf=tf,
                positions=token_positions[token],
                title_tf=title_freq.get(token, 0),
            )
            if token not in terms:
                terms[token] = TermEntry(df=0, postings={})
            terms[token].postings[doc_id] = posting
            terms[token].df += 1

    metadata: dict[str, str | int] = {
        "created_at": datetime.now(UTC).isoformat(),
        "num_documents": len(documents),
        "num_terms": len(terms),
        "source_url": source_url,
        "version": "1.0",
    }

    return SearchIndex(metadata=metadata, documents=documents, terms=terms)
