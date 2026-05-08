# Performance Benchmarks

## Environment

- **Machine:** Apple Silicon (ARM64), macOS
- **Python:** 3.14
- **Index:** 4,646 terms across 202 documents (~2.6 MB JSON)

## How to Reproduce

```bash
python -m scripts.benchmark --runs 50
```

Benchmarks are local and reproducible. They are not included in CI to avoid flaky assertions.

## Results

### Index Load Time (50 runs)

| Metric | Value |
|--------|-------|
| Median | 37.4 ms |
| Mean   | 49.5 ms |
| Stdev  | 32.2 ms |

Loading a ~2.6 MB JSON index into fully typed Python dataclasses completes in under 40 ms at the median. This is fast enough that `load` feels instantaneous in the CLI.

### Query Latency (50 runs each)

| Query | Median (ms) | Results |
|-------|-------------|---------|
| `world` | 0.040 | 43 |
| `einstein` | 0.030 | 33 |
| `good friends` | 0.022 | 13 |
| `love humor inspirational` | 0.011 | 4 |
| `xyznonexistent` | 0.001 | 0 |

All queries complete in sub-millisecond time. The conjunctive AND intersection + TF-IDF scoring + phrase detection pipeline is efficient for a corpus of this size.

### Posting List Sizes (Top 10 by Document Frequency)

| Term | df | Total occurrences |
|------|----|-------------------|
| quotes | 202 | 206 |
| to | 202 | 761 |
| scrape | 202 | 202 |
| a | 139 | 684 |
| the | 135 | 1,205 |
| is | 118 | 319 |
| and | 113 | 710 |
| of | 111 | 725 |
| it | 91 | 222 |
| that | 90 | 186 |

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
