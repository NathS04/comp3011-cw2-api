"""One-off script to crawl the live site and build the index."""

import time

from src.crawler import BASE_URL, crawl
from src.indexer import build_index
from src.storage import save_index

print(f"Starting crawl of {BASE_URL}...")
print("Politeness window: 6 seconds between requests")
print("Expected time: ~20 minutes for ~200 pages")
print()

start = time.time()
count = [0]


def on_page(r):  # type: ignore[no-untyped-def]
    count[0] += 1
    elapsed = time.time() - start
    print(f"  [{count[0]:3d}] {elapsed:6.1f}s  {r.url}")


pages = crawl(BASE_URL, on_page=on_page)
elapsed = time.time() - start
print(f"\nCrawled {len(pages)} pages in {elapsed:.1f}s")

print("Building index...")
index = build_index(pages, source_url=BASE_URL)
num_terms = index.metadata["num_terms"]
num_docs = index.metadata["num_documents"]
print(f"Index: {num_terms} terms across {num_docs} documents")

print("Saving to data/index.json...")
save_index(index, "data/index.json")
print("Done!")
