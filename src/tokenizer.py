"""Text extraction and tokenization for the search engine.

Tokenization policy (justified from COMP3011 lecture material):
- Lowercase all text (requirement: case-insensitive search).
- Keep contractions as single tokens (e.g. "it's", "don't").
- Hyphens split words (e.g. "deep-thoughts" -> ["deep", "thoughts"]).
- Numbers are kept (dates like "1879" may be searched).
- Pure punctuation is discarded.
- No stopword removal (preserves correctness for queries like "to be or not to be").
- No stemming (keeps exact-match behaviour predictable and testable).
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def tokenize(text: str) -> list[str]:
    """Split *text* into a list of normalised tokens.

    Returns lowercase alphanumeric tokens.  Contractions like "it's" are
    preserved as one token.  Hyphens, punctuation, and whitespace act as
    separators.
    """
    return _TOKEN_PATTERN.findall(text.lower())


def _text(element: Tag | Any) -> str:
    """Safely extract text from a BS4 element."""
    if element and hasattr(element, "get_text"):
        result: str = element.get_text(strip=True)
        return result
    return ""


def _text_sep(element: Tag | Any) -> str:
    """Safely extract text with space separator from a BS4 element."""
    if element and hasattr(element, "get_text"):
        result: str = element.get_text(separator=" ", strip=True)
        return result
    return ""


# ---------------------------------------------------------------------------
# HTML text extraction
# ---------------------------------------------------------------------------

def extract_page_text(html: str) -> tuple[str, str]:
    """Return ``(title_text, body_text)`` extracted from *html*.

    ``title_text`` comes from the ``<title>`` tag (or ``<h1>`` fallback).
    ``body_text`` is the concatenation of all meaningful visible text on the
    page -- quotes, author names, tags, biographies, etc.
    """
    soup = BeautifulSoup(html, "html.parser")

    title_text = _text(soup.find("title"))

    body_parts: list[str] = []

    quotes = soup.find_all("div", class_="quote")
    if quotes:
        for quote in quotes:
            text_span = _text(quote.find("span", class_="text"))
            if text_span:
                body_parts.append(text_span)

            author_name = _text(quote.find("small", class_="author"))
            if author_name:
                body_parts.append(author_name)

            for tag_link in quote.find_all("a", class_="tag"):
                tag_text = _text(tag_link)
                if tag_text:
                    body_parts.append(tag_text)

    author_details = soup.find("div", class_="author-details")
    if author_details and isinstance(author_details, Tag):
        author_title = _text(author_details.find("h3", class_="author-title"))
        if author_title:
            body_parts.append(author_title)

        born_date = _text(author_details.find("span", class_="author-born-date"))
        if born_date:
            body_parts.append(born_date)

        born_loc = _text(author_details.find("span", class_="author-born-location"))
        if born_loc:
            body_parts.append(born_loc)

        description = _text(author_details.find("div", class_="author-description"))
        if description:
            body_parts.append(description)

    if not body_parts:
        body_text = _text_sep(soup.find("body"))
        if body_text:
            body_parts.append(body_text)

    return title_text, " ".join(body_parts)
