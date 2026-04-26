"""Query engine — print and find commands with TF-IDF ranking.

Search design (from COMP3011 Lectures 12-13):
- ``print <word>``: displays the inverted-index entry for that term.
- ``find <words>``: conjunctive (AND) retrieval over posting lists,
  ranked by log-normalised TF-IDF with a title-field boost and an
  optional exact-phrase adjacency bonus.

Ranking formula:
    score(doc, query) = SUM over each query term t of:
        (1 + log10(tf)) * log10(N / df) * title_boost

    title_boost = 2.0 if the term appears in the document title, else 1.0
    phrase_bonus = 1.5x multiplier if all query terms appear consecutively
"""

from __future__ import annotations

import difflib
import math
from dataclasses import dataclass

from src.models import SearchIndex
from src.tokenizer import tokenize

TITLE_BOOST = 2.0
PHRASE_BONUS = 1.5


@dataclass
class SearchResult:
    """A single document returned by ``find``."""

    doc_id: str
    url: str
    title: str
    score: float


# ---------------------------------------------------------------------------
# Posting-list intersection (conjunctive AND)
# ---------------------------------------------------------------------------

def intersect_postings(index: SearchIndex, terms: list[str]) -> set[str]:
    """Return doc_ids containing *all* of *terms*."""
    if not terms:
        return set()

    postings_sets: list[set[str]] = []
    for term in terms:
        entry = index.terms.get(term)
        if entry is None:
            return set()
        postings_sets.append(set(entry.postings.keys()))

    postings_sets.sort(key=len)
    result = postings_sets[0]
    for s in postings_sets[1:]:
        result = result & s
        if not result:
            break
    return result


# ---------------------------------------------------------------------------
# TF-IDF scoring
# ---------------------------------------------------------------------------

def _tfidf_score(
    index: SearchIndex,
    doc_id: str,
    query_terms: list[str],
) -> float:
    """Compute the TF-IDF score for *doc_id* given *query_terms*."""
    n = len(index.documents)
    if n == 0:
        return 0.0

    score = 0.0
    for term in query_terms:
        entry = index.terms.get(term)
        if entry is None or doc_id not in entry.postings:
            continue
        posting = entry.postings[doc_id]
        tf_weight = 1.0 + math.log10(posting.tf) if posting.tf > 0 else 0.0
        idf = math.log10(n / entry.df) if entry.df > 0 else 0.0
        boost = TITLE_BOOST if posting.title_tf > 0 else 1.0
        score += tf_weight * idf * boost

    return score


# ---------------------------------------------------------------------------
# Exact-phrase detection using positions
# ---------------------------------------------------------------------------

def _has_exact_phrase(
    index: SearchIndex,
    doc_id: str,
    query_terms: list[str],
) -> bool:
    """Check whether *query_terms* appear as a consecutive phrase in *doc_id*."""
    if len(query_terms) < 2:
        return False

    first_term = query_terms[0]
    first_entry = index.terms.get(first_term)
    if first_entry is None or doc_id not in first_entry.postings:
        return False

    start_positions = first_entry.postings[doc_id].positions

    for start_pos in start_positions:
        match = True
        for offset, term in enumerate(query_terms[1:], start=1):
            entry = index.terms.get(term)
            if entry is None or doc_id not in entry.postings:
                match = False
                break
            if (start_pos + offset) not in entry.postings[doc_id].positions:
                match = False
                break
        if match:
            return True
    return False


# ---------------------------------------------------------------------------
# Public query API
# ---------------------------------------------------------------------------

def print_term(index: SearchIndex, word: str) -> str:
    """Return a formatted string showing the index entry for *word*."""
    tokens = tokenize(word)
    if not tokens:
        return "No valid term provided."

    term = tokens[0]
    entry = index.terms.get(term)
    if entry is None:
        suggestions = get_suggestions(index, term)
        msg = f"Term '{term}' not found in index."
        if suggestions:
            msg += f"\n  Did you mean: {', '.join(suggestions)}?"
        return msg

    lines: list[str] = [
        f"Term: '{term}'",
        f"  Document frequency (df): {entry.df}",
        "  Postings:",
    ]
    for doc_id, posting in sorted(entry.postings.items()):
        doc = index.documents[doc_id]
        lines.append(
            f"    {doc_id} | {doc.url}"
            f" | tf={posting.tf}"
            f" | title_tf={posting.title_tf}"
            f" | positions={posting.positions}"
        )
    return "\n".join(lines)


def find(index: SearchIndex, query: str) -> list[SearchResult]:
    """Find pages matching *query* (conjunctive AND), ranked by TF-IDF.

    Returns an empty list if any query term is absent from the index.
    """
    query_terms = tokenize(query)
    if not query_terms:
        return []

    unique_terms = list(dict.fromkeys(query_terms))
    matching_docs = intersect_postings(index, unique_terms)
    if not matching_docs:
        return []

    scored: list[SearchResult] = []
    for doc_id in matching_docs:
        score = _tfidf_score(index, doc_id, unique_terms)
        if _has_exact_phrase(index, doc_id, unique_terms):
            score *= PHRASE_BONUS
        doc = index.documents[doc_id]
        scored.append(SearchResult(
            doc_id=doc_id,
            url=doc.url,
            title=doc.title,
            score=score,
        ))

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored


def get_suggestions(index: SearchIndex, term: str, n: int = 5) -> list[str]:
    """Suggest index terms close to *term* using edit distance."""
    return difflib.get_close_matches(term, index.terms.keys(), n=n, cutoff=0.6)
