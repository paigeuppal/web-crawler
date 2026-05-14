"""Search Engine Shell — entry point.

Run from the repository root:
    python src/main.py

Supported commands:
    build          Crawl the website, build the index, and save it.
    load           Load a previously saved index from disk.
    print <word>   Print the index entry for a word.
    find <w> ...   List all pages containing every supplied word.
    help           Show available commands.
    quit           Exit the shell.
"""

import json
import os
import sys

# Allow imports from this directory when run as a script
sys.path.insert(0, os.path.dirname(__file__))

from crawler import crawl
from indexer import build_index
from search import print_word, rank_pages

TARGET_URL = "https://quotes.toscrape.com/"
INDEX_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "index.json")


def cmd_build() -> dict:
    print(f"Starting crawl of {TARGET_URL} …")
    pages = crawl(TARGET_URL)
    print(f"\nCrawled {len(pages)} page(s). Building index …")
    index = build_index(pages)
    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as fh:
        json.dump(index, fh)
    print(f"Index saved to {INDEX_FILE}  ({len(index)} unique words).")
    return index


def cmd_load() -> dict | None:
    if not os.path.exists(INDEX_FILE):
        print("No index file found. Run 'build' first.")
        return None
    with open(INDEX_FILE, encoding="utf-8") as fh:
        index = json.load(fh)
    print(f"Index loaded from {INDEX_FILE}  ({len(index)} unique words).")
    return index


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
                "  quit               - exit\n"
            )
        elif command == "quit":
            break
        elif command == "build":
            index = cmd_build()
        elif command == "load":
            index = cmd_load()
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
                results = rank_pages(index, args)
                if results:
                    print(f"  Found {len(results)} page(s) (ranked by relevance):")
                    for url, score in results:
                        print(f"    [{score:.4f}]  {url}")
                else:
                    print("  No pages found.")
        else:
            print(f"  Unknown command: '{command}'. Type 'help' for commands.")


if __name__ == "__main__":
    run_shell()
