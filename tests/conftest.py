"""Shared pytest fixtures for the search-engine test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def page1_html() -> str:
    return (FIXTURES_DIR / "page1.html").read_text(encoding="utf-8")


@pytest.fixture()
def page2_html() -> str:
    return (FIXTURES_DIR / "page2.html").read_text(encoding="utf-8")


@pytest.fixture()
def author_html() -> str:
    return (FIXTURES_DIR / "author.html").read_text(encoding="utf-8")
