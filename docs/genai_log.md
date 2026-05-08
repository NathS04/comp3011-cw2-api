# GenAI Usage Log — COMP3011 Coursework 2

## Tools Used

- **GitHub Copilot** (via the University of Leeds secure Copilot access) — AI coding assistant used throughout development for code suggestions, API guidance, and test scaffolding.

## Usage Log

| Date | Tool | Prompt/Task | What AI Suggested | Correct/Incorrect | What I Changed | Learning Impact |
|------|------|-------------|-------------------|--------------------|----------------|-----------------|
| Week 1 | Copilot | "How to extract text from specific CSS classes in BeautifulSoup" | Showed `soup.find_all('span', class_='text')` and explained `find` vs `find_all` vs CSS `select` | Correct | Used as-is but also read BS4 docs to understand when to use `.select()` vs `.find_all()` | Saved 30 min learning the API; reading the docs myself gave deeper understanding of the parser differences |
| Week 1 | Copilot | "Generate a tokenizer for search engine text" | Suggested `text.split()` followed by `strip(string.punctuation)` | Partially incorrect | Rejected. This failed on contractions: `it's` became `it` and `s`. Redesigned using `re.findall(r"[a-z0-9]+(?:'[a-z]+)?", ...)` | Learned that AI-generated regex needs systematic edge-case testing; wrote 24 unit tests for the tokenizer |
| Week 2 | Copilot | "Design an inverted index data structure" | Suggested `dict[str, list[int]]` mapping terms to document IDs | Partially correct but insufficient | The brief requires word statistics (frequency, positions). I designed a richer structure with `Posting(tf, positions, title_tf)` based on Lecture 12 slides on inverted indices | AI's default was a toy index; the brief demanded more |
| Week 2 | Copilot | "Generate test cases for the tokenizer" | Produced 8 basic tests (lowercase, split on space, remove punctuation) | Correct but incomplete | Added 16 more tests manually: unicode smart quotes, HTML entities, empty strings, whitespace-only, hyphenated words, contractions, trailing apostrophes, numbers with text | AI test suites tend toward happy-path coverage and miss edge cases |
| Week 3 | Copilot | "Implement retry logic for the crawler" | Suggested using the `tenacity` library for exponential backoff | Technically sound but inappropriate | Rejected external dependency. Wrote a simple 3-attempt for-loop with `time.sleep(6 * attempt)`. Fully understandable and explainable | AI defaults to library solutions; for coursework, simplicity and explainability are more important |
| Week 3 | Copilot | "Serialize Python dataclasses to JSON" | Suggested `dataclasses.asdict()` for serialisation; deserialisation code had a bug (didn't reconstruct Posting objects from dicts) | Partially correct | Kept `asdict()` idea but wrote custom `to_dict()` / `from_dict()` class methods with explicit type handling | Debugging AI's deserialisation code taught me more about Python type coercion than just writing it from scratch would have |
| Week 4 | Manual | Implemented TF-IDF ranking without AI | N/A — deliberate choice | N/A | Worked from formula: `tf_weight = 1 + log10(tf)`, `idf = log10(N/df)`, directly from Lecture 12 and the Croft textbook | Slower but I can derive and explain every line. This is the core algorithmic contribution |
| Week 4 | Copilot | "How to do edit-distance-based word suggestions in Python" | Showed `difflib.get_close_matches()` with correct usage | Correct | Used as suggested with `cutoff=0.6` and `n=5` | Standard library solution was exactly right; no modification needed |

## Critical Reflections

### Where AI Helped Most
AI was most valuable for **API lookup** (BeautifulSoup selectors, `difflib` usage, JSON serialisation patterns) and **boilerplate generation** (test file scaffolding, CI config). These are tasks where correctness is verifiable and the knowledge is factual.

### Where AI Hindered or Was Insufficient
AI was weakest on **design decisions that require understanding the assessment brief** (inverted index structure, tokenization policy, dependency choices). It also consistently generated **incomplete test suites** that covered happy paths but missed important edge cases.

### Impact on Learning
The most valuable learning came from **debugging AI's incorrect suggestions** (tokenizer regex, deserialisation bug) and from **deliberately implementing core algorithms manually** (TF-IDF, posting-list intersection). When AI generates working code quickly, the temptation is to move on without understanding — I mitigated this by writing algorithmic code first, then comparing with AI suggestions.

### Ethical Considerations
Using AI for a coursework assessment raises a fairness question: students with AI tools can scaffold projects faster. However, the 15% GenAI evaluation mark rewards *critical thinking about* AI, not just *usage of* AI. The requirement to explain every line of code in the video demo ensures that AI-assisted code must still be fully understood. I used only the University's secure Copilot access as recommended in the brief.
