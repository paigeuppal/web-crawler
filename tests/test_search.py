"""Tests for the search module."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from search import find_pages, print_word, rank_pages

# ---------------------------------------------------------------------------
# Shared fixture — includes _meta for TF-IDF tests
# ---------------------------------------------------------------------------

INDEX = {
    "_meta": {
        "doc_count": 2,
        "doc_lengths": {
            "http://example.com/1": 10,
            "http://example.com/2": 10,
        },
    },
    "hello": {
        "http://example.com/1": {"frequency": 2, "positions": [0, 5]},
        "http://example.com/2": {"frequency": 1, "positions": [3]},
    },
    "world": {
        "http://example.com/1": {"frequency": 1, "positions": [1]},
    },
    "python": {
        "http://example.com/2": {"frequency": 1, "positions": [0]},
    },
}

# ---------------------------------------------------------------------------
# find_pages
# ---------------------------------------------------------------------------

def test_find_single_word_returns_all_pages():
    results = find_pages(INDEX, ["hello"])
    assert "http://example.com/1" in results
    assert "http://example.com/2" in results


def test_find_multi_word_intersection():
    results = find_pages(INDEX, ["hello", "world"])
    assert results == ["http://example.com/1"]


def test_find_no_matching_pages():
    results = find_pages(INDEX, ["nonexistent"])
    assert results == []


def test_find_empty_query():
    assert find_pages(INDEX, []) == []


def test_find_all_whitespace_query():
    # Covers the `if not words: return []` branch (line 36)
    assert find_pages(INDEX, ["   "]) == []


def test_find_second_word_absent():
    # Covers the `return []` inside the for loop (line 45) — first word
    # exists in index but the second does not at all
    assert find_pages(INDEX, ["hello", "zzzznotaword"]) == []


def test_find_case_insensitive():
    results = find_pages(INDEX, ["HELLO"])
    assert "http://example.com/1" in results


def test_find_multi_word_no_overlap():
    results = find_pages(INDEX, ["world", "python"])
    assert results == []


def test_find_returns_sorted_urls():
    results = find_pages(INDEX, ["hello"])
    assert results == sorted(results)


def test_find_whitespace_in_query_ignored():
    results = find_pages(INDEX, ["  hello  "])
    assert "http://example.com/1" in results


# ---------------------------------------------------------------------------
# print_word
# ---------------------------------------------------------------------------

def test_print_word_found(capsys):
    print_word(INDEX, "hello")
    captured = capsys.readouterr()
    assert "hello" in captured.out
    assert "http://example.com/1" in captured.out


def test_print_word_not_found(capsys):
    print_word(INDEX, "notaword")
    captured = capsys.readouterr()
    assert "not found" in captured.out


def test_print_word_case_insensitive(capsys):
    print_word(INDEX, "HELLO")
    captured = capsys.readouterr()
    assert "hello" in captured.out


def test_print_word_empty_string(capsys):
    print_word(INDEX, "")
    captured = capsys.readouterr()
    assert "Usage" in captured.out


# ---------------------------------------------------------------------------
# rank_pages (TF-IDF)
# ---------------------------------------------------------------------------

def test_rank_pages_returns_matching_pages():
    results = rank_pages(INDEX, ["hello"])
    urls = [url for url, _ in results]
    assert "http://example.com/1" in urls
    assert "http://example.com/2" in urls


def test_rank_pages_higher_frequency_ranks_first():
    # example.com/1 has frequency 2 for "hello", example.com/2 has frequency 1
    # so example.com/1 should rank higher
    results = rank_pages(INDEX, ["hello"])
    assert results[0][0] == "http://example.com/1"


def test_rank_pages_scores_are_positive():
    results = rank_pages(INDEX, ["hello"])
    for _, score in results:
        assert score > 0


def test_rank_pages_empty_query():
    assert rank_pages(INDEX, []) == []


def test_rank_pages_no_match():
    assert rank_pages(INDEX, ["nonexistent"]) == []


def test_rank_pages_multi_word_only_returns_intersection():
    results = rank_pages(INDEX, ["hello", "world"])
    urls = [url for url, _ in results]
    assert urls == ["http://example.com/1"]


def test_rank_pages_scores_are_floats():
    results = rank_pages(INDEX, ["hello"])
    for _, score in results:
        assert isinstance(score, float)
