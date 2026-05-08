"""Command-line interface for the search engine tool.

Provides an interactive shell with the four required commands:
    build  — crawl the website, build the index, save to disk
    load   — load a previously built index from disk
    print  — display the inverted-index entry for a word
    find   — find pages containing all query terms
    quit   — exit the shell
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.crawler import BASE_URL, crawl
from src.indexer import build_index
from src.models import SearchIndex
from src.search import find, get_suggestions, print_term
from src.storage import load_index, save_index
from src.tokenizer import tokenize

DEFAULT_INDEX_PATH = Path("data/index.json")


class SearchShell:
    """Interactive command-line shell for the search tool."""

    def __init__(self, index_path: Path = DEFAULT_INDEX_PATH) -> None:
        self.index: SearchIndex | None = None
        self.index_path = index_path

    def do_build(self) -> None:
        """Crawl the website, build the index, and save it."""
        print(f"Crawling {BASE_URL} (this may take ~20 minutes due to politeness window)...")

        pages = crawl(
            BASE_URL,
            on_page=lambda r: print(f"  Crawled: {r.url}"),
        )
        print(f"\nCrawled {len(pages)} pages.")

        print("Building inverted index...")
        self.index = build_index(pages, source_url=BASE_URL)
        print(
            f"Index built: {self.index.metadata['num_terms']} terms "
            f"across {self.index.metadata['num_documents']} documents."
        )

        save_index(self.index, self.index_path)
        print(f"Index saved to {self.index_path}")

    def do_load(self) -> None:
        """Load the index from disk."""
        try:
            self.index = load_index(self.index_path)
        except FileNotFoundError:
            print(
                f"Error: No index file found at {self.index_path}. "
                "Run 'build' first."
            )
            return
        except (json.JSONDecodeError, KeyError, OSError, UnicodeDecodeError) as exc:
            print(f"Error loading index: {exc}")
            return

        print(
            f"Index loaded: {self.index.metadata['num_terms']} terms, "
            f"{self.index.metadata['num_documents']} documents."
        )

    def do_print(self, args: str) -> None:
        """Print the inverted-index entry for a word."""
        if self.index is None:
            print("Error: No index loaded. Run 'build' or 'load' first.")
            return
        if not args.strip():
            print("Usage: print <word>")
            return
        print(print_term(self.index, args.strip()))

    def do_find(self, args: str) -> None:
        """Find pages containing the query terms."""
        if self.index is None:
            print("Error: No index loaded. Run 'build' or 'load' first.")
            return
        if not args.strip():
            print("Usage: find <word1> [word2] ...")
            return

        results = find(self.index, args)
        if not results:
            query_terms = tokenize(args)
            print(f"No pages found containing all terms: {query_terms}")
            for term in query_terms:
                suggestions = get_suggestions(self.index, term)
                if suggestions:
                    print(f"  Suggestions for '{term}': {', '.join(suggestions)}")
            return

        print(f"Found {len(results)} page(s):\n")
        for i, result in enumerate(results, 1):
            print(
                f"  {i}. [{result.score:.4f}] {result.title}\n"
                f"     {result.url}"
            )

    def run(self) -> None:
        """Start the interactive shell loop."""
        print("COMP3011 Search Engine Tool")
        print("Commands: build, load, print <word>, find <query>, quit\n")

        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break

            if not line:
                continue

            parts = line.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            if command == "build":
                self.do_build()
            elif command == "load":
                self.do_load()
            elif command == "print":
                self.do_print(args)
            elif command == "find":
                self.do_find(args)
            elif command in ("quit", "exit"):
                print("Goodbye.")
                break
            else:
                print(f"Unknown command: '{command}'. Try: build, load, print, find, quit")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    shell = SearchShell()
    shell.run()


if __name__ == "__main__":
    main()
