"""Search operations against the inverted index.

Provides the logic for the 'print' and 'find' shell commands, including
TF-IDF ranked retrieval for multi-term queries.

TF-IDF formula used:
    TF(term, doc)  = frequency(term, doc) / doc_length(doc)
    IDF(term)      = log(1 + total_docs / docs_containing_term)
    score(doc)     = sum of TF-IDF for each query term present in doc

IDF is smoothed with +1 inside the log to avoid division-by-zero when
every document contains the term.
"""

import math


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
    """Return a sorted list of URLs containing every word in query_words.

    Performs an intersection of posting lists so only pages matching all
    terms are returned. Results are in alphabetical URL order.
    Use rank_pages() instead when relevance ordering is needed.
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


def rank_pages(index: dict, query_words: list[str]) -> list[tuple[str, float]]:
    """Return pages containing all query words, ranked by TF-IDF score.

    Returns a list of (url, score) tuples sorted by score descending.
    Pages not containing every query term are excluded.
    """
    candidate_urls = find_pages(index, query_words)
    if not candidate_urls:
        return []

    words = [w.lower().strip() for w in query_words if w.strip()]
    meta = index.get("_meta", {})
    total_docs = meta.get("doc_count", len(candidate_urls))
    doc_lengths = meta.get("doc_lengths", {})

    scored: list[tuple[str, float]] = []

    for url in candidate_urls:
        score = 0.0
        doc_length = doc_lengths.get(url, 1)

        for word in words:
            freq = index[word][url]["frequency"]
            df = len(index[word])
            tf = freq / doc_length
            idf = math.log(1 + total_docs / df)
            score += tf * idf

        scored.append((url, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
