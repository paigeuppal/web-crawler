"""Tests for the indexer module."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from indexer import tokenise, build_index, STOPWORDS

# ---------------------------------------------------------------------------
# tokenise
# ---------------------------------------------------------------------------

def test_tokenise_basic():
    assert tokenise("Hello World") == ["hello", "world"]


def test_tokenise_case_insensitive():
    assert tokenise("Good GOOD good") == ["good", "good", "good"]


def test_tokenise_strips_punctuation():
    assert tokenise("hello, world!") == ["hello", "world"]


def test_tokenise_numbers_ignored():
    assert tokenise("page 42 results") == ["page", "results"]


def test_tokenise_empty_string():
    assert tokenise("") == []


def test_tokenise_whitespace_only():
    assert tokenise("   ") == []


# ---------------------------------------------------------------------------
# STOPWORDS
# ---------------------------------------------------------------------------

def test_stopwords_is_frozenset():
    assert isinstance(STOPWORDS, frozenset)


def test_stopwords_contains_common_words():
    for word in ("the", "a", "is", "and", "in"):
        assert word in STOPWORDS


def test_stopwords_does_not_contain_content_words():
    for word in ("python", "crawler", "index", "search"):
        assert word not in STOPWORDS


# ---------------------------------------------------------------------------
# build_index
# ---------------------------------------------------------------------------

def test_build_index_frequency():
    pages = {"http://example.com/": "hello world hello"}
    index = build_index(pages)
    assert index["hello"]["http://example.com/"]["frequency"] == 2


def test_build_index_positions():
    # Use non-stopword tokens; positions reflect the full token stream.
    # "cat" is at 0, "dog" at 1, "fox" at 2, "cat" at 3.
    pages = {"http://example.com/": "cat dog fox cat"}
    index = build_index(pages)
    assert index["cat"]["http://example.com/"]["positions"] == [0, 3]
    assert index["dog"]["http://example.com/"]["positions"] == [1]


def test_build_index_excludes_stopwords():
    pages = {"http://example.com/": "the quick brown fox"}
    index = build_index(pages)
    assert "the" not in index
    assert "quick" in index
    assert "brown" in index
    assert "fox" in index


def test_build_index_stopword_positions_preserved():
    # "the" is skipped but "cat" appears at position 1 in the full stream,
    # not position 0 — positions are not re-numbered after filtering.
    pages = {"http://example.com/": "the cat"}
    index = build_index(pages)
    assert index["cat"]["http://example.com/"]["positions"] == [1]


def test_build_index_multiple_pages():
    pages = {
        "http://example.com/1": "hello world",
        "http://example.com/2": "hello python",
    }
    index = build_index(pages)
    assert len(index["hello"]) == 2
    assert "http://example.com/1" in index["hello"]
    assert "http://example.com/2" in index["hello"]


def test_build_index_case_insensitive():
    pages = {"http://example.com/": "Good good GOOD"}
    index = build_index(pages)
    assert "good" in index
    assert index["good"]["http://example.com/"]["frequency"] == 3
    assert "Good" not in index
    assert "GOOD" not in index


def test_build_index_empty_input():
    index = build_index({})
    assert index["_meta"]["doc_count"] == 0
    assert index["_meta"]["doc_lengths"] == {}


def test_build_index_empty_page_text():
    pages = {"http://example.com/": ""}
    index = build_index(pages)
    assert index["_meta"]["doc_count"] == 1
    assert index["_meta"]["doc_lengths"]["http://example.com/"] == 0


def test_build_index_stores_doc_count():
    pages = {
        "http://example.com/1": "hello world",
        "http://example.com/2": "foo bar",
    }
    index = build_index(pages)
    assert index["_meta"]["doc_count"] == 2


def test_build_index_doc_length_includes_stopwords():
    # doc_length counts ALL tokens (including stopwords) so TF values
    # remain comparable across pages of different lengths.
    pages = {"http://example.com/": "the quick brown fox"}
    index = build_index(pages)
    assert index["_meta"]["doc_lengths"]["http://example.com/"] == 4


def test_build_index_stores_doc_lengths():
    pages = {"http://example.com/": "hello world hello"}
    index = build_index(pages)
    assert index["_meta"]["doc_lengths"]["http://example.com/"] == 3
