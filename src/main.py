"""Search Engine Shell — entry point.

Run from the repository root:
    python src/main.py

Supported commands:
    build          Crawl the website, build the index, and save it.
    load           Load a previously saved index from disk.
    print <word>   Print the index entry for a word.
    find <w> ...   List all pages containing every supplied word.
    stats          Show index statistics.
    help           Show available commands.
    quit           Exit the shell.
"""

import json
import os
import sys

# Allow imports from this directory when run as a script
sys.path.insert(0, os.path.dirname(__file__))

from crawler import crawl
from indexer import build_index, STOPWORDS
from search import get_stats, print_word, rank_pages

TARGET_URL = "https://quotes.toscrape.com/"
INDEX_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "index.json")
)


def cmd_build() -> dict:
    print(f"Starting crawl of {TARGET_URL} …")
    pages = crawl(TARGET_URL)
    print(f"\nCrawled {len(pages)} page(s). Building index …")
    index = build_index(pages)
    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as fh:
        json.dump(index, fh)
    word_count = len(index) - 1  # exclude _meta key
    print(f"Index saved to {INDEX_FILE}  ({word_count:,} unique words).")
    return index


def cmd_load() -> dict | None:
    if not os.path.exists(INDEX_FILE):
        print("No index file found. Run 'build' first.")
        return None
    with open(INDEX_FILE, encoding="utf-8") as fh:
        index = json.load(fh)
    word_count = len(index) - 1  # exclude _meta key
    print(f"Index loaded from {INDEX_FILE}  ({word_count:,} unique words).")
    return index


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
        elif command == "load":
            index = cmd_load()
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
                print_word(index, args[0])
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

                if not search_words:
                    print("  No searchable words in query.")
                else:
                    results = rank_pages(index, search_words)
                    if results:
                        print(f"  Found {len(results)} page(s) (ranked by relevance):")
                        for url, score in results:
                            print(f"    [{score:.4f}]  {url}")
                    else:
                        print("  No pages found.")
        else:
            print(f"  Unknown command: '{command}'. Type 'help' for commands.")


if __name__ == "__main__":  # pragma: no cover
    run_shell()
