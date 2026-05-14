"""Inverted index builder.

Tokenises plain-text page content and builds an index with per-word,
per-page frequency and position statistics.
"""

import re


def tokenise(text: str) -> list[str]:
    """Return a list of lowercase alphabetic tokens from text."""
    return re.findall(r"[a-z]+", text.lower())


def build_index(pages: dict[str, str]) -> dict:
    """Build an inverted index from a mapping of URL -> plain text.

    Index structure:
        {
            word: {
                url: {
                    "frequency": int,
                    "positions": [int, ...]
                }
            }
        }
    """
    index: dict = {}

    for url, text in pages.items():
        tokens = tokenise(text)
        for position, word in enumerate(tokens):
            if word not in index:
                index[word] = {}
            if url not in index[word]:
                index[word][url] = {"frequency": 0, "positions": []}
            index[word][url]["frequency"] += 1
            index[word][url]["positions"].append(position)

    return index
