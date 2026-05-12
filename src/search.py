"""Search operations against the inverted index.

Provides the logic for the 'print' and 'find' shell commands.
"""


def print_word(index: dict, word: str) -> None:
    """Print the full inverted index entry for a single word."""
    word = word.lower().strip()
    if not word:
        print("Usage: print <word>")
        return
    if word not in index:
        print(f"  '{word}' not found in index.")
        return

    entries = index[word]
    print(f"  '{word}' appears in {len(entries)} page(s):\n")
    for url, stats in entries.items():
        print(f"  URL       : {url}")
        print(f"  Frequency : {stats['frequency']}")
        print(f"  Positions : {stats['positions']}\n")


def find_pages(index: dict, query_words: list[str]) -> list[str]:
    """Return a sorted list of URLs that contain every word in query_words.

    Performs an intersection across the posting lists of all query terms,
    so only pages matching all words are returned.
    """
    if not query_words:
        return []

    words = [w.lower().strip() for w in query_words if w.strip()]
    if not words:
        return []

    if words[0] not in index:
        return []

    result_urls: set[str] = set(index[words[0]].keys())

    for word in words[1:]:
        if word not in index:
            return []
        result_urls &= set(index[word].keys())

    return sorted(result_urls)
