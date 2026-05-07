#!/usr/bin/env python3
"""Performance benchmarks for the search engine.

Measures index load time, query latency, and reports index statistics.
Results are printed to stdout in a format suitable for docs/benchmarks.md.

Usage:
    python scripts/benchmark.py [--index data/index.json] [--runs 50]
"""

from __future__ import annotations

import argparse
import os
import statistics
import time
from pathlib import Path

from src.search import find
from src.storage import load_index


def _time_fn(fn: object, runs: int) -> list[float]:
    """Run *fn* (a callable) *runs* times and return elapsed times in ms."""
    times: list[float] = []
    callable_fn = fn  # type: ignore[assignment]
    for _ in range(runs):
        start = time.perf_counter()
        callable_fn()
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    return times


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark the search engine")
    parser.add_argument(
        "--index", default="data/index.json", help="Path to the index file"
    )
    parser.add_argument(
        "--runs", type=int, default=50, help="Number of repetitions per measurement"
    )
    args = parser.parse_args()

    index_path = Path(args.index)
    if not index_path.exists():
        print(f"Error: index file not found at {index_path}")
        print("Run 'python -m src.main' and use the 'build' command first.")
        raise SystemExit(1)

    runs: int = args.runs

    print("=" * 60)
    print("COMP3011 Search Engine — Performance Benchmarks")
    print("=" * 60)

    file_size = os.path.getsize(index_path)
    print(f"\nIndex file:  {index_path}")
    print(f"File size:   {file_size / 1024:.1f} KB ({file_size / (1024 * 1024):.2f} MB)")

    # --- Index load time ---
    load_times = _time_fn(lambda: load_index(index_path), runs)
    print(f"\n--- Index Load ({runs} runs) ---")
    print(f"  Median: {statistics.median(load_times):.2f} ms")
    print(f"  Mean:   {statistics.mean(load_times):.2f} ms")
    print(f"  Stdev:  {statistics.stdev(load_times):.2f} ms")

    index = load_index(index_path)
    num_docs = len(index.documents)
    num_terms = len(index.terms)
    print(f"\nIndex stats: {num_terms} terms, {num_docs} documents")

    # --- Query latency ---
    queries = [
        "world",
        "einstein",
        "good friends",
        "love humor inspirational",
        "xyznonexistent",
    ]

    print(f"\n--- Query Latency ({runs} runs each) ---")
    print(f"  {'Query':<35} {'Median ms':>10} {'Results':>8}")
    print(f"  {'-' * 35} {'-' * 10} {'-' * 8}")

    for query in queries:
        times = _time_fn(lambda q=query: find(index, q), runs)  # type: ignore[misc]
        results = find(index, query)
        median = statistics.median(times)
        print(f"  {query:<35} {median:>10.3f} {len(results):>8}")

    # --- Posting-list intersection scaling ---
    print("\n--- Posting List Sizes (top 10 by df) ---")
    print(f"  {'Term':<20} {'df':>6} {'Total postings':>15}")
    print(f"  {'-' * 20} {'-' * 6} {'-' * 15}")

    sorted_terms = sorted(index.terms.items(), key=lambda t: t[1].df, reverse=True)
    for term, entry in sorted_terms[:10]:
        total_postings = sum(p.tf for p in entry.postings.values())
        print(f"  {term:<20} {entry.df:>6} {total_postings:>15}")

    print("\n" + "=" * 60)
    print("Benchmarks are local and reproducible. Not used in CI.")
    print("=" * 60)


if __name__ == "__main__":
    main()
