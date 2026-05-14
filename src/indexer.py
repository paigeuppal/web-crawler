"""Inverted index builder.

Tokenises plain-text page content and builds an index with per-word,
per-page frequency and position statistics, plus document-length metadata
required for TF-IDF scoring at query time.
"""

import re


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

    The _meta section stores the document lengths needed to compute
    term frequency (TF = raw_frequency / doc_length) at query time.
    """
    index: dict = {"_meta": {"doc_count": 0, "doc_lengths": {}}}

    for url, text in pages.items():
        tokens = tokenise(text)
        index["_meta"]["doc_lengths"][url] = len(tokens)
        index["_meta"]["doc_count"] += 1

        for position, word in enumerate(tokens):
            if word not in index:
                index[word] = {}
            if url not in index[word]:
                index[word][url] = {"frequency": 0, "positions": []}
            index[word][url]["frequency"] += 1
            index[word][url]["positions"].append(position)

    return index
