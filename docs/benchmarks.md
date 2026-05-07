# Performance Benchmarks

## Environment

- **Machine:** Apple Silicon (ARM64), macOS
- **Python:** 3.14
- **Index:** 4,646 terms across 202 documents (~2.7 MB JSON)

## How to Reproduce

```bash
python -m scripts.benchmark --runs 50
```

Benchmarks are local and reproducible. They are not included in CI to avoid flaky assertions.

## Results

### Index Load Time (50 runs)

| Metric | Value |
|--------|-------|
| Median | 28.5 ms |
| Mean   | 31.7 ms |
| Stdev  | 13.3 ms |

Loading a ~2.8 MB JSON index into fully typed Python dataclasses completes in under 30 ms at the median. This is fast enough that `load` feels instantaneous in the CLI.

### Query Latency (50 runs each)

| Query | Median (ms) | Results |
|-------|-------------|---------|
| `world` | 0.043 | 48 |
| `einstein` | 0.032 | 36 |
| `good friends` | 0.032 | 19 |
| `love humor inspirational` | 0.011 | 4 |
| `xyznonexistent` | 0.001 | 0 |

All queries complete in sub-millisecond time. The conjunctive AND intersection + TF-IDF scoring + phrase detection pipeline is efficient for a corpus of this size.

### Posting List Sizes (Top 10 by Document Frequency)

| Term | df | Total occurrences |
|------|----|-------------------|
| quotes | 212 | 218 |
| to | 212 | 833 |
| scrape | 212 | 212 |
| a | 149 | 750 |
| the | 144 | 1,275 |
| is | 128 | 392 |
| and | 122 | 764 |
| of | 120 | 777 |
| it | 100 | 263 |
| that | 98 | 219 |

These common terms appear in most documents. The posting-list intersection starts from the shortest list, so multi-term queries with at least one selective term are fast.

## Complexity Analysis

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| **Crawl** | O(P) | P = number of pages; each page fetched exactly once via BFS |
| **Index build** | O(P × W) | W = average tokens per page; single pass over all tokens |
| **Index load** | O(T × D̄) | T = terms, D̄ = average postings per term; JSON deserialisation |
| **Query (find)** | O(K₁ + K₂ + ... + Kₙ) | Kᵢ = posting list length; intersection starts from shortest |
| **Phrase detection** | O(S × Q) | S = candidate start positions, Q = query term count |
| **TF-IDF scoring** | O(M × Q) | M = matched documents, Q = query terms |

The dominant cost in practice is the crawl (network-bound, ~20 minutes with 6-second politeness). All in-memory operations complete in milliseconds.
