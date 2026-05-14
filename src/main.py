"""Search Engine Shell - entry point.

Run from the repository root:
    python src/main.py

Supported commands:
    build          Crawl the website, build the index, and save it.
    load           Load a previously saved index from disk.
    print <word>   Print the index entry for a word, with suggestions if not found.
    find <w> ...   List pages containing every word, ranked by TF-IDF score.
                   Shows a text snippet for each result. Suggests alternatives
                   for unknown words. Notes stopwords in the query.
    stats          Show index statistics.
    help           Show available commands.
    quit           Exit the shell.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from crawler import crawl
from indexer import build_index, STOPWORDS
from search import (
    best_snippet_position, extract_snippet,
    get_stats, print_word, rank_pages, suggest,
)

TARGET_URL = "https://quotes.toscrape.com/"
INDEX_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "index.json")
)
PAGES_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "pages.json")
)


def cmd_build() -> dict:
    print(f"Starting crawl of {TARGET_URL} …")
    pages = crawl(TARGET_URL)
    print(f"\nCrawled {len(pages)} page(s). Building index …")
    index = build_index(pages)
    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as fh:
        json.dump(index, fh)
    with open(PAGES_FILE, "w", encoding="utf-8") as fh:
        json.dump(pages, fh)
    word_count = len(index) - 1
    print(f"Index saved to {INDEX_FILE}  ({word_count:,} unique words).")
    return index


def cmd_load() -> dict | None:
    if not os.path.exists(INDEX_FILE):
        print("No index file found. Run 'build' first.")
        return None
    with open(INDEX_FILE, encoding="utf-8") as fh:
        index = json.load(fh)
    word_count = len(index) - 1
    print(f"Index loaded from {INDEX_FILE}  ({word_count:,} unique words).")
    return index


def load_pages() -> dict | None:
    """Load page texts from disk for snippet extraction. Returns None if unavailable."""
    if not os.path.exists(PAGES_FILE):
        return None
    with open(PAGES_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def cmd_stats(index: dict) -> None:
    """Print a summary of index statistics to stdout."""
    s = get_stats(index)
    sep = "─" * 48
    print(f"\n  Index Statistics")
    print(f"  {sep}")
    print(f"  Pages indexed    : {s['doc_count']:>6,}")
    print(f"  Unique words     : {s['word_count']:>6,}")
    print(f"  Total tokens     : {s['total_tokens']:>6,}")
    print(f"  Avg words / page : {s['avg_tokens']:>6.0f}")
    print(f"\n  Top 10 words by page coverage:")
    for word, df in s["top_words"]:
        print(f"    {word:<18} → {df:,} page(s)")
    if s["longest"]:
        url, length = s["longest"]
        print(f"\n  Longest page  ({length:,} tokens) : {url}")
    if s["shortest"]:
        url, length = s["shortest"]
        print(f"  Shortest page  ({length:,} tokens) : {url}")
    print()


def run_shell() -> None:
    index: dict | None = None
    pages: dict | None = None
    print("Search Engine Shell — type 'help' for commands, 'quit' to exit.\n")

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue

        parts = line.split()
        command = parts[0].lower()
        args = parts[1:]

        if command == "help":
            print(
                "  build              – crawl site and build index\n"
                "  load               – load index from disk\n"
                "  print <word>       – print index entry for a word\n"
                "  find <word> [...]  – find pages containing all words\n"
                "  stats              – show index statistics\n"
                "  quit               – exit\n"
            )
        elif command == "quit":
            break
        elif command == "build":
            index = cmd_build()
            pages = load_pages()
        elif command == "load":
            index = cmd_load()
            pages = load_pages()
        elif command == "stats":
            if index is None:
                print("No index loaded. Run 'build' or 'load' first.")
            else:
                cmd_stats(index)
        elif command == "print":
            if not args:
                print("Usage: print <word>")
            elif index is None:
                print("No index loaded. Run 'build' or 'load' first.")
            else:
                word = args[0].lower().strip()
                print_word(index, word)
                if word not in index and word not in STOPWORDS:
                    hints = suggest(index, word)
                    if hints:
                        print(f"  Did you mean: {', '.join(hints[:3])}?")
        elif command == "find":
            if not args:
                print("Usage: find <word> [word ...]")
            elif index is None:
                print("No index loaded. Run 'build' or 'load' first.")
            else:
                words = [w.lower() for w in args]
                sw_hit = [w for w in words if w in STOPWORDS]
                search_words = [w for w in words if w not in STOPWORDS]

                if sw_hit:
                    listed = ", ".join(f"'{w}'" for w in sw_hit)
                    label = "is a stopword" if len(sw_hit) == 1 else "are stopwords"
                    print(f"  Note: {listed} {label} excluded from the index.")

                unknown = [w for w in search_words if w not in index]
                for w in unknown:
                    hints = suggest(index, w)
                    if hints:
                        print(f"  '{w}' not in index. Did you mean: {', '.join(hints[:3])}?")
                    else:
                        print(f"  '{w}' not in index.")

                valid_words = [w for w in search_words if w in index]
                if not valid_words:
                    print("  No searchable words in query.")
                else:
                    results = rank_pages(index, valid_words)
                    if results:
                        print(f"  Found {len(results)} page(s) (ranked by relevance):")
                        for url, score in results:
                            print(f"    [{score:.4f}]  {url}")
                            if pages and url in pages:
                                pos = best_snippet_position(index, valid_words, url)
                                snippet = extract_snippet(pages[url], pos)
                                print(f"             \"{snippet}\"")
                    else:
                        print("  No pages found.")
        else:
            print(f"  Unknown command: '{command}'. Type 'help' for commands.")


if __name__ == "__main__":  # pragma: no cover
    run_shell()
