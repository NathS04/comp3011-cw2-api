"""Tests for the CLI shell (main.py)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.indexer import build_index
from src.main import SearchShell
from src.models import CrawlResult
from src.storage import save_index

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _build_test_index(tmp_path: Path) -> Path:
    """Build and save a small index, return path to the JSON file."""
    pages = [
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
    ]
    index = build_index(pages, source_url="http://test.com")
    index_path = tmp_path / "index.json"
    save_index(index, index_path)
    return index_path


class TestSearchShell:
    def test_load_success(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        index_path = _build_test_index(tmp_path)
        shell = SearchShell(index_path=index_path)
        shell.do_load()
        captured = capsys.readouterr()
        assert "loaded" in captured.out.lower()
        assert shell.index is not None

    def test_load_missing_file(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        shell = SearchShell(index_path=tmp_path / "nope.json")
        shell.do_load()
        captured = capsys.readouterr()
        assert "error" in captured.out.lower()
        assert shell.index is None

    def test_print_without_index(self, capsys: pytest.CaptureFixture[str]) -> None:
        shell = SearchShell()
        shell.do_print("world")
        captured = capsys.readouterr()
        assert "no index" in captured.out.lower()

    def test_print_empty_arg(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        index_path = _build_test_index(tmp_path)
        shell = SearchShell(index_path=index_path)
        shell.do_load()
        capsys.readouterr()

        shell.do_print("")
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower()

    def test_print_existing_term(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        index_path = _build_test_index(tmp_path)
        shell = SearchShell(index_path=index_path)
        shell.do_load()
        capsys.readouterr()

        shell.do_print("world")
        captured = capsys.readouterr()
        assert "world" in captured.out
        assert "tf=" in captured.out

    def test_print_missing_term(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        index_path = _build_test_index(tmp_path)
        shell = SearchShell(index_path=index_path)
        shell.do_load()
        capsys.readouterr()

        shell.do_print("xyznonexistent")
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()

    def test_find_without_index(self, capsys: pytest.CaptureFixture[str]) -> None:
        shell = SearchShell()
        shell.do_find("world")
        captured = capsys.readouterr()
        assert "no index" in captured.out.lower()

    def test_find_empty_arg(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        index_path = _build_test_index(tmp_path)
        shell = SearchShell(index_path=index_path)
        shell.do_load()
        capsys.readouterr()

        shell.do_find("")
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower()

    def test_find_existing_term(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        index_path = _build_test_index(tmp_path)
        shell = SearchShell(index_path=index_path)
        shell.do_load()
        capsys.readouterr()

        shell.do_find("world")
        captured = capsys.readouterr()
        assert "found" in captured.out.lower()

    def test_find_missing_term(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        index_path = _build_test_index(tmp_path)
        shell = SearchShell(index_path=index_path)
        shell.do_load()
        capsys.readouterr()

        shell.do_find("xyznonexistent")
        captured = capsys.readouterr()
        assert "no pages found" in captured.out.lower()

    def test_find_multi_word(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        index_path = _build_test_index(tmp_path)
        shell = SearchShell(index_path=index_path)
        shell.do_load()
        capsys.readouterr()

        shell.do_find("albert einstein")
        captured = capsys.readouterr()
        assert "found" in captured.out.lower()

    def test_run_quit(self, capsys: pytest.CaptureFixture[str]) -> None:
        shell = SearchShell()
        with patch("builtins.input", return_value="quit"):
            shell.run()
        captured = capsys.readouterr()
        assert "goodbye" in captured.out.lower()

    def test_run_exit(self, capsys: pytest.CaptureFixture[str]) -> None:
        shell = SearchShell()
        with patch("builtins.input", return_value="exit"):
            shell.run()
        captured = capsys.readouterr()
        assert "goodbye" in captured.out.lower()

    def test_run_unknown_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        shell = SearchShell()
        with patch("builtins.input", side_effect=["foobar", "quit"]):
            shell.run()
        captured = capsys.readouterr()
        assert "unknown command" in captured.out.lower()

    def test_run_empty_input(self, capsys: pytest.CaptureFixture[str]) -> None:
        shell = SearchShell()
        with patch("builtins.input", side_effect=["", "quit"]):
            shell.run()
        captured = capsys.readouterr()
        assert "goodbye" in captured.out.lower()

    def test_run_eof(self, capsys: pytest.CaptureFixture[str]) -> None:
        shell = SearchShell()
        with patch("builtins.input", side_effect=EOFError):
            shell.run()
        captured = capsys.readouterr()
        assert "goodbye" in captured.out.lower()

    def test_run_keyboard_interrupt(self, capsys: pytest.CaptureFixture[str]) -> None:
        shell = SearchShell()
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            shell.run()
        captured = capsys.readouterr()
        assert "goodbye" in captured.out.lower()

    def test_run_load_command(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        index_path = _build_test_index(tmp_path)
        shell = SearchShell(index_path=index_path)
        with patch("builtins.input", side_effect=["load", "quit"]):
            shell.run()
        captured = capsys.readouterr()
        assert "loaded" in captured.out.lower()

    def test_run_print_command(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        index_path = _build_test_index(tmp_path)
        shell = SearchShell(index_path=index_path)
        with patch("builtins.input", side_effect=["load", "print world", "quit"]):
            shell.run()
        captured = capsys.readouterr()
        assert "tf=" in captured.out

    def test_run_find_command(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        index_path = _build_test_index(tmp_path)
        shell = SearchShell(index_path=index_path)
        with patch("builtins.input", side_effect=["load", "find world", "quit"]):
            shell.run()
        captured = capsys.readouterr()
        assert "found" in captured.out.lower()
