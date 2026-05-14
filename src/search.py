"""Search operations against the inverted index.

Provides the logic for the 'print', 'find', and 'stats' shell commands,
including TF-IDF ranked retrieval, query suggestions, and snippet extraction.

TF-IDF formula used:
    TF(term, doc)  = frequency(term, doc) / doc_length(doc)
    IDF(term)      = log(1 + total_docs / docs_containing_term)
    score(doc)     = sum of TF-IDF for each query term present in doc

IDF is smoothed with +1 inside the log to avoid division-by-zero when
every document contains the term.
"""

import math
import re


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


def get_stats(index: dict) -> dict:
    """Compute summary statistics from the inverted index.

    Returns a dict with:
        doc_count    – number of pages indexed
        word_count   – number of unique non-stopword words
        total_tokens – sum of all page token counts (including stopwords)
        avg_tokens   – average tokens per page
        top_words    – list of (word, doc_frequency) sorted by df descending
        longest      – (url, token_count) for the longest page
        shortest     – (url, token_count) for the shortest page
    """
    meta = index.get("_meta", {})
    doc_count = meta.get("doc_count", 0)
    doc_lengths: dict[str, int] = meta.get("doc_lengths", {})

    words = [k for k in index if k != "_meta"]
    word_count = len(words)
    total_tokens = sum(doc_lengths.values())
    avg_tokens = total_tokens / doc_count if doc_count else 0.0

    top_words = sorted(
        ((word, len(index[word])) for word in words),
        key=lambda x: x[1],
        reverse=True,
    )[:10]

    longest = max(doc_lengths.items(), key=lambda x: x[1]) if doc_lengths else None
    shortest = min(doc_lengths.items(), key=lambda x: x[1]) if doc_lengths else None

    return {
        "doc_count": doc_count,
        "word_count": word_count,
        "total_tokens": total_tokens,
        "avg_tokens": avg_tokens,
        "top_words": top_words,
        "longest": longest,
        "shortest": shortest,
    }


def _edit_distance(a: str, b: str) -> int:
    """Compute the Levenshtein edit distance between strings a and b.

    Returns early with 3 if the length difference exceeds 2, avoiding
    unnecessary computation for clearly dissimilar words.
    """
    if abs(len(a) - len(b)) > 2:
        return 3
    m, n = len(a), len(b)
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        curr = [i] + [0] * n
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1]
            else:
                curr[j] = 1 + min(prev[j - 1], prev[j], curr[j - 1])
        prev = curr
    return prev[n]


def suggest(index: dict, word: str, max_results: int = 5) -> list[str]:
    """Return index words similar to word, for use as query suggestions.

    Strategy:
        1. Prefix match — find words starting with the first 4 chars of word.
           Fast O(W) scan; handles completions (e.g. 'indif' → 'indifference').
        2. Edit distance fallback — if no prefix matches, find words within
           Levenshtein distance ≤ 2. Handles typos (e.g. 'helo' → 'hello').

    Words shorter than 2 characters are ignored as too ambiguous.
    """
    word = word.lower().strip()
    if len(word) < 2:
        return []

    candidates = [k for k in index if k != "_meta"]
    prefix = word[:min(4, len(word))]
    prefix_matches = sorted(
        [w for w in candidates if w.startswith(prefix) and w != word],
        key=len,
    )
    if prefix_matches:
        return prefix_matches[:max_results]

    close = [
        (w, _edit_distance(word, w))
        for w in candidates
        if w != word and _edit_distance(word, w) <= 2
    ]
    close.sort(key=lambda x: x[1])
    return [w for w, _ in close[:max_results]]


def extract_snippet(page_text: str, position: int, context: int = 5) -> str:
    """Extract a readable text snippet around the token at position.

    Uses the full token stream (including stopwords) so the snippet reads
    as natural prose. Surrounding ellipses indicate truncation.

    Args:
        page_text: The plain-text content of the page.
        position:  Token index of the target word in the full token stream.
        context:   Number of tokens to include on each side of the target.
    """
    tokens = re.findall(r"[a-z]+", page_text.lower())
    if not tokens or position >= len(tokens):
        return ""
    start = max(0, position - context)
    end = min(len(tokens), position + context + 1)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(tokens) else ""
    return f"{prefix}{' '.join(tokens[start:end])}{suffix}"
