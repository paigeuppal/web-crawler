"""Tests for the search module."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from search import find_pages, print_word

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

INDEX = {
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
