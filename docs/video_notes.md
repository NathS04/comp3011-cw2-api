# Video Demo Script — COMP3011 Coursework 2

Target duration: **4 minutes 40 seconds** (20-second buffer under the 5-minute limit).

## 0:00–0:10 — Introduction (10s)

- "This is my COMP3011 search engine tool for quotes.toscrape.com."
- Briefly show the repo structure in the IDE file tree.

## 0:10–2:00 — Live Demonstration (1 min 50s)

**Pre-requisite:** Index has been pre-built (full crawl takes ~20 minutes).

1. **`build`** — Show the command starting, explain "6-second politeness window, BFS crawl of ~200 pages". Switch to pre-built output.
2. **`load`** — Run live. "Loading the index — 4500 terms, 200 documents."
3. **`print nonsense`** — Show posting list. Explain tf, positions, df.
4. **`print world`** — Show a term with multiple documents.
5. **`find indifference`** — Single-word search. "Conjunctive AND retrieval, ranked by TF-IDF."
6. **`find good friends`** — Multi-word AND search. Point out TF-IDF scores and phrase boost.
7. **Edge cases:**
   - `find xyznotaword` — "No pages found, but suggests similar terms."
   - `find` (empty) — "Clear usage message."
   - `print zzzzz` — "Term not found, with suggestions."

## 2:00–3:30 — Code Walkthrough (1 min 30s)

Open and briefly explain key sections:

1. **`src/crawler.py`** — "BFS with deque frontier, visited set, injectable sleep function for testing, retry with exponential backoff."
2. **`src/indexer.py`** — "Builds inverted index. Each posting stores tf, positions, and title_tf."
3. **`src/search.py`** — "Posting list intersection for AND queries. TF-IDF: `1 + log10(tf)` times `log10(N/df)` with 2x title boost. Phrase adjacency bonus checks positions."
4. **`src/models.py`** — "Dataclass-based, fully typed. Custom `to_dict`/`from_dict` for clean JSON serialisation."
5. **Design choice:** "JSON for index storage — human-readable and inspectable."

## 3:30–4:00 — Testing (30s)

Run: `pytest --cov=src --cov-report=term-missing -v`

- "136 tests, 93% coverage."
- "Includes unit, integration, and mocked network tests."
- Point at one test: "This test mocks `requests.Session` to verify the crawler retries on HTTP 500 errors without hitting the network."

## 4:00–4:30 — Version Control (30s)

Run: `git log --oneline --graph -20`

- "30+ commits using conventional commit messages across feature branches."
- "Tagged releases at v0.1, v0.2, v1.0."
- Show one merge: "feature/ranking developed separately then merged to main."

## 4:30–5:00 — GenAI Evaluation (30s)

- "I used Cursor with Claude as my AI assistant throughout development."
- "AI was helpful for BeautifulSoup API guidance and fixture generation."
- "But I had to fix its tokenizer — it broke contractions like 'it's'."
- "I deliberately implemented TF-IDF ranking without AI to ensure I understood the algorithm from Lecture 12."
- "Full usage log with reflections is in `docs/genai_log.md`."

## Checklist Before Recording

- [ ] Index file pre-built and saved in `data/index.json`
- [ ] Terminal font size large enough to be legible at 720p
- [ ] Audio levels tested
- [ ] All demo commands listed in a cheat sheet
- [ ] Practice run completed under 4:40
- [ ] Video hosted on YouTube (unlisted) or OneDrive
- [ ] Link tested in incognito browser
