"""Tests for tokenization and HTML text extraction."""

from __future__ import annotations

from src.tokenizer import extract_page_text, tokenize

# ── tokenize() unit tests ────────────────────────────────────────────────

class TestTokenize:
    def test_basic_words(self) -> None:
        assert tokenize("the world is big") == ["the", "world", "is", "big"]

    def test_lowercase_conversion(self) -> None:
        assert tokenize("HELLO") == ["hello"]

    def test_mixed_case(self) -> None:
        assert tokenize("GoOd FrIeNdS") == ["good", "friends"]

    def test_contractions_preserved(self) -> None:
        assert tokenize("it's a beautiful day") == ["it's", "a", "beautiful", "day"]

    def test_dont_contraction(self) -> None:
        assert tokenize("don't stop") == ["don't", "stop"]

    def test_apostrophe_possessive(self) -> None:
        assert tokenize("einstein's theory") == ["einstein's", "theory"]

    def test_hyphens_split(self) -> None:
        assert tokenize("deep-thoughts") == ["deep", "thoughts"]

    def test_numbers_kept(self) -> None:
        assert tokenize("born in 1879") == ["born", "in", "1879"]

    def test_numbers_with_text(self) -> None:
        assert tokenize("e=mc2") == ["e", "mc2"]

    def test_punctuation_stripped(self) -> None:
        assert tokenize("hello, world!") == ["hello", "world"]

    def test_period_stripped(self) -> None:
        assert tokenize("end of sentence.") == ["end", "of", "sentence"]

    def test_empty_string(self) -> None:
        assert tokenize("") == []

    def test_whitespace_only(self) -> None:
        assert tokenize("   ") == []

    def test_repeated_spaces(self) -> None:
        assert tokenize("hello    world") == ["hello", "world"]

    def test_smart_quotes_stripped(self) -> None:
        assert tokenize("\u201cHello\u201d") == ["hello"]

    def test_curly_single_quotes(self) -> None:
        assert tokenize("\u2018word\u2019") == ["word"]

    def test_html_entity_apostrophe(self) -> None:
        """Text already decoded by BS4 should still tokenize correctly."""
        assert tokenize("it's") == ["it's"]

    def test_tabs_and_newlines(self) -> None:
        assert tokenize("hello\tworld\nfoo") == ["hello", "world", "foo"]

    def test_special_characters_only(self) -> None:
        assert tokenize("!@#$%^&*()") == []

    def test_colon_semicolon(self) -> None:
        assert tokenize("note: important; yes") == ["note", "important", "yes"]

    def test_slash_separator(self) -> None:
        assert tokenize("either/or") == ["either", "or"]

    def test_trailing_apostrophe(self) -> None:
        # A trailing apostrophe without continuation is not a contraction
        assert tokenize("dogs'") == ["dogs"]

    def test_unicode_dash(self) -> None:
        assert tokenize("self\u2014aware") == ["self", "aware"]

    def test_ellipsis(self) -> None:
        assert tokenize("wait... what") == ["wait", "what"]


# ── extract_page_text() tests ────────────────────────────────────────────

class TestExtractPageText:
    def test_quote_page_title(self, page1_html: str) -> None:
        title, _ = extract_page_text(page1_html)
        assert title == "Quotes to Scrape"

    def test_quote_page_body_contains_quote(self, page1_html: str) -> None:
        _, body = extract_page_text(page1_html)
        assert "world" in body.lower()
        assert "thinking" in body.lower()

    def test_quote_page_body_contains_author(self, page1_html: str) -> None:
        _, body = extract_page_text(page1_html)
        assert "Albert Einstein" in body

    def test_quote_page_body_contains_tags(self, page1_html: str) -> None:
        _, body = extract_page_text(page1_html)
        assert "change" in body.lower()
        assert "deep-thoughts" in body.lower()

    def test_author_page_extracts_name(self, author_html: str) -> None:
        _, body = extract_page_text(author_html)
        assert "Albert Einstein" in body

    def test_author_page_extracts_born_date(self, author_html: str) -> None:
        _, body = extract_page_text(author_html)
        assert "1879" in body

    def test_author_page_extracts_location(self, author_html: str) -> None:
        _, body = extract_page_text(author_html)
        assert "Ulm" in body

    def test_author_page_extracts_description(self, author_html: str) -> None:
        _, body = extract_page_text(author_html)
        assert "photoelectric" in body.lower()

    def test_page2_body_contains_friend(self, page2_html: str) -> None:
        _, body = extract_page_text(page2_html)
        assert "friend" in body.lower()

    def test_page2_body_contains_jim_morrison(self, page2_html: str) -> None:
        _, body = extract_page_text(page2_html)
        assert "Jim Morrison" in body
