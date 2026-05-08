# COMP3011 Search Engine Tool

A command-line search engine for [quotes.toscrape.com](https://quotes.toscrape.com/) built as Coursework 2 for COMP3011 Web Services and Web Data at the University of Leeds.

The tool crawls the target website, builds an inverted index with term frequencies and word positions, and provides an interactive shell for searching.

## Features

- **BFS web crawler** with 6-second politeness window, retry/backoff, and URL normalisation.
- **Inverted index** storing term frequency, word positions, document frequency, and title-field frequency per posting.
- **Conjunctive (AND) search** — multi-word queries return only pages containing all terms.
- **TF-IDF ranking** — results are ranked by log-normalised TF × IDF with a title-field boost.
- **Exact phrase search** — wrap a query in double quotes (`find "good friends"`) to require consecutive term positions. Unquoted queries still apply a 1.5× score boost for phrase matches.
- **Query suggestions** — misspelled terms trigger edit-distance-based suggestions from the index vocabulary.
- **JSON index storage** — human-readable, portable, inspectable by markers.

## Architecture

```
                   ┌──────────┐
                   │  main.py │  CLI shell (build / load / print / find)
                   └────┬─────┘
            ┌───────────┼───────────┐
            ▼           ▼           ▼
      ┌──────────┐ ┌──────────┐ ┌──────────┐
      │crawler.py│ │indexer.py│ │ search.py│
      │ BFS      │ │ build    │ │ TF-IDF   │
      │ politenes│ │ inv.index│ │ phrase   │
      └────┬─────┘ └────┬─────┘ └────┬─────┘
           │             │            │
      ┌────▼─────┐ ┌─────▼────┐ ┌────▼─────┐
      │tokenizer │ │ models.py│ │storage.py│
      │ BS4 parse│ │dataclasse│ │ JSON I/O │
      └──────────┘ └──────────┘ └──────────┘
```

**Data flow:** `crawl → extract_page_text → tokenize → build_index → save_index` (build), then `load_index → find/print_term` (query).

## Project Structure

```
src/
  main.py        — CLI shell entry point
  crawler.py     — BFS web crawler
  indexer.py     — Inverted index builder
  search.py      — Print/find query engine with TF-IDF ranking
  tokenizer.py   — HTML text extraction and tokenization
  storage.py     — JSON serialisation/deserialisation
  models.py      — Shared dataclasses
tests/
  test_crawler.py, test_indexer.py, test_search.py, ...
  test_regression.py — Invariant and regression tests
  fixtures/      — Static HTML for deterministic offline tests
scripts/
  benchmark.py   — Performance measurement script
data/
  index.json     — Generated index file (after running 'build')
docs/
  benchmarks.md  — Performance results and complexity analysis
  genai_log.md   — GenAI usage log and critical reflections
  video_notes.md — 5-minute video demo script
```

## Installation

Requires **Python 3.11+**.

```bash
# Clone the repository
git clone https://github.com/NathS04/comp3011-cw2-api.git
cd comp3011-cw2-api

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

Start the interactive shell:

```bash
python -m src.main
```

### Commands

**`build`** — Crawl the website, build the index, and save it to `data/index.json`.

```
> build
Crawling https://quotes.toscrape.com (this may take ~20 minutes due to politeness window)...
  Crawled: https://quotes.toscrape.com/page/1
  Crawled: https://quotes.toscrape.com/page/2
  ...
Crawled 202 pages.
Index built: 4646 terms across 202 documents.
Index saved to data/index.json
```

**`load`** — Load a previously saved index from disk.

```
> load
Index loaded: 4646 terms, 202 documents.
```

**`print <word>`** — Display the inverted-index entry for a word.

```
> print nonsense
Term: 'nonsense'
  Document frequency (df): 5
  Postings:
    doc_0035 | https://quotes.toscrape.com/page/2 | tf=1 | title_tf=0 | positions=[501]
    doc_0038 | https://quotes.toscrape.com/tag/life | tf=1 | title_tf=0 | positions=[541]
    doc_0082 | https://quotes.toscrape.com/tag/regrets | tf=1 | title_tf=0 | positions=[154]
    doc_0135 | https://quotes.toscrape.com/tag/fantasy | tf=1 | title_tf=0 | positions=[105]
    doc_0185 | https://quotes.toscrape.com/page/7 | tf=1 | title_tf=0 | positions=[396]
```

**`find <query>`** — Find pages containing all query terms, ranked by TF-IDF.

```
> find good friends
Found 13 page(s):

  1. [4.8444] Quotes to Scrape
     https://quotes.toscrape.com/tag/friends
  2. [4.7657] Quotes to Scrape
     https://quotes.toscrape.com/page/2
  3. [4.5733] Quotes to Scrape
     https://quotes.toscrape.com/tag/life
  ...
```

Wrap the query in double quotes for **exact phrase** matching (terms must appear consecutively):

```
> find "good friends"
Found 6 page(s):

  1. [4.8444] Quotes to Scrape
     https://quotes.toscrape.com/tag/friends
  2. [4.7657] Quotes to Scrape
     https://quotes.toscrape.com/page/2
  3. [4.5733] Quotes to Scrape
     https://quotes.toscrape.com/tag/life
  ...
```

**`quit`** — Exit the shell.

## Testing

Run the full test suite:

```bash
pytest -v
```

Run with coverage report:

```bash
pytest --cov=src --cov-report=term-missing -v
```

The project targets 90%+ code coverage. Tests use local HTML fixture files and mocked HTTP responses — no network access is required.

### Test Categories

| Category | Files | Description |
|----------|-------|-------------|
| Unit | `test_tokenizer.py` | Tokenization edge cases |
| Unit | `test_crawler.py` | URL normalisation, BFS, mocked retries |
| Unit | `test_indexer.py` | Index building, tf/positions/df verification |
| Unit | `test_storage.py` | JSON roundtrip, error handling |
| Unit | `test_search.py` | Query, ranking, phrase boost, suggestions |
| Unit | `test_main.py` | CLI shell commands and I/O |
| Integration | `test_integration.py` | Full build→save→load→find pipeline |
| Regression | `test_regression.py` | Canonical URLs, deterministic ordering, index invariants |

## Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | HTTP client for web crawling |
| `beautifulsoup4` | HTML parsing and text extraction |
| `pytest` | Test framework |
| `pytest-cov` | Coverage measurement |
| `coverage` | Coverage reporting |
| `ruff` | Linting (PEP 8, import sorting) |
| `mypy` | Static type checking |

## Benchmarks

Performance benchmarks are in [`docs/benchmarks.md`](docs/benchmarks.md). To reproduce:

```bash
python -m scripts.benchmark --runs 50
```

Key results (Apple Silicon, Python 3.11+):

| Operation | Median |
|-----------|--------|
| Index load (~2.6 MB) | 37.4 ms |
| Single-word query | 0.04 ms |
| Multi-word query | 0.02 ms |
| Missing term | 0.001 ms |

All queries complete in sub-millisecond time. See `docs/benchmarks.md` for full complexity analysis.

## Design Decisions

### Tokenization
- Lowercase conversion for case-insensitive search.
- Contractions preserved as single tokens (`it's`, `don't`).
- Hyphens split words (`deep-thoughts` → `deep`, `thoughts`).
- No stopword removal — preserves correctness for queries like `"to be or not to be"`.
- No stemming — keeps exact-match behaviour predictable.

### Index Storage
JSON was chosen over pickle or SQLite because it is human-readable, portable, and allows markers to inspect the index file directly.

### Ranking
Log-normalised TF-IDF with title-field weighting, based on the formula from COMP3011 Lecture 12:

```
score = Σ (1 + log₁₀(tf)) × log₁₀(N/df) × title_boost
```

Where `title_boost = 2.0` if the term appears in the page title.

### Complexity Analysis
- **Crawl:** O(P) where P is the number of pages, each fetched once via BFS.
- **Index build:** O(P × W) where W is the average number of words per page.
- **Query (find):** O(K₁ + K₂ + ... + Kₙ) where Kᵢ is the length of each term's posting list, using set intersection starting from the shortest list.
- **Phrase detection:** O(S × Q) where S is the number of starting positions and Q is the number of query terms.
