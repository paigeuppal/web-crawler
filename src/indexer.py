"""Inverted index builder.

Tokenises plain-text page content and builds an index with per-word,
per-page frequency and position statistics, plus document-length metadata
required for TF-IDF scoring at query time.

Stopwords (common function words like 'the', 'a', 'is') are excluded from
the index. This reduces index size and improves TF-IDF quality because
stopwords carry no discriminating signal across documents.
"""

import re

# Classic English stopwords — high-frequency function words that add noise
# to the index without improving search precision.
STOPWORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "not",
    "no", "nor", "so", "yet", "both", "either", "neither", "each", "few",
    "more", "most", "other", "some", "such", "than", "too", "very", "just",
    "that", "this", "these", "those", "it", "its", "i", "me", "my", "we",
    "our", "you", "your", "he", "she", "her", "his", "they", "their",
    "them", "who", "which", "what", "if", "then", "there", "when", "where",
    "how", "all", "any", "about", "into", "through", "during", "before",
    "after", "above", "below", "up", "down", "out", "off", "over", "under",
    "again", "here", "only", "own", "same", "s", "t",
})


def tokenise(text: str) -> list[str]:
    """Return a list of lowercase alphabetic tokens from text."""
    return re.findall(r"[a-z]+", text.lower())


def build_index(pages: dict[str, str]) -> dict:
    """Build an inverted index from a mapping of URL -> plain text.

    Index structure:
        {
            "_meta": {
                "doc_count": int,
                "doc_lengths": {url: int}   # total token count per page
            },
            word: {
                url: {
                    "frequency": int,
                    "positions": [int, ...]
                }
            }
        }

    Stopwords are excluded from word entries. doc_length counts all tokens
    (including stopwords) so that TF values remain comparable across pages
    of different lengths.

    Positions reflect each word's index in the full token stream, not the
    filtered stream, so they correctly represent location within the page.
    """
    index: dict = {"_meta": {"doc_count": 0, "doc_lengths": {}}}

    for url, text in pages.items():
        tokens = tokenise(text)
        index["_meta"]["doc_lengths"][url] = len(tokens)
        index["_meta"]["doc_count"] += 1

        for position, word in enumerate(tokens):
            if word in STOPWORDS:
                continue
            if word not in index:
                index[word] = {}
            if url not in index[word]:
                index[word][url] = {"frequency": 0, "positions": []}
            index[word][url]["frequency"] += 1
            index[word][url]["positions"].append(position)

    return index
