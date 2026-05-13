"""Tests for the search module and CLI shell commands."""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import patch

from search import find_pages, print_word, rank_pages
from main import run_shell

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


# ---------------------------------------------------------------------------
# CLI shell — run_shell
# ---------------------------------------------------------------------------

def test_shell_quit_exits_cleanly():
    with patch("builtins.input", side_effect=["quit"]):
        run_shell()


def test_shell_eof_exits_cleanly():
    with patch("builtins.input", side_effect=EOFError):
        run_shell()


def test_shell_keyboard_interrupt_exits_cleanly():
    with patch("builtins.input", side_effect=KeyboardInterrupt):
        run_shell()


def test_shell_empty_lines_ignored(capsys):
    with patch("builtins.input", side_effect=["", "   ", "quit"]):
        run_shell()
    assert "Unknown" not in capsys.readouterr().out


def test_shell_unknown_command(capsys):
    with patch("builtins.input", side_effect=["xyz", "quit"]):
        run_shell()
    assert "unknown" in capsys.readouterr().out.lower()


def test_shell_help_lists_all_commands(capsys):
    with patch("builtins.input", side_effect=["help", "quit"]):
        run_shell()
    out = capsys.readouterr().out
    for cmd in ("build", "load", "print", "find", "quit"):
        assert cmd in out


def test_shell_find_without_index(capsys):
    with patch("builtins.input", side_effect=["find hello", "quit"]):
        run_shell()
    assert "no index" in capsys.readouterr().out.lower()


def test_shell_print_without_index(capsys):
    with patch("builtins.input", side_effect=["print hello", "quit"]):
        run_shell()
    assert "no index" in capsys.readouterr().out.lower()


def test_shell_find_no_args(capsys):
    with patch("builtins.input", side_effect=["find", "quit"]):
        run_shell()
    assert "usage" in capsys.readouterr().out.lower()


def test_shell_print_no_args(capsys):
    with patch("builtins.input", side_effect=["print", "quit"]):
        run_shell()
    assert "usage" in capsys.readouterr().out.lower()


def test_shell_build_command(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    sample_pages = {"http://example.com/1": "hello world"}
    with patch("main.crawl", return_value=sample_pages), \
         patch("main.build_index", return_value=INDEX), \
         patch("main.INDEX_FILE", str(index_file)), \
         patch("builtins.input", side_effect=["build", "quit"]):
        run_shell()
    assert "saved" in capsys.readouterr().out.lower()


def test_shell_load_then_find_returns_results(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(INDEX))
    with patch("main.INDEX_FILE", str(index_file)), \
         patch("builtins.input", side_effect=["load", "find hello", "quit"]):
        run_shell()
    assert "http://example.com/1" in capsys.readouterr().out


def test_shell_load_then_find_ranked_by_score(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(INDEX))
    with patch("main.INDEX_FILE", str(index_file)), \
         patch("builtins.input", side_effect=["load", "find hello", "quit"]):
        run_shell()
    out = capsys.readouterr().out
    assert "[" in out and "]" in out
    assert out.index("example.com/1") < out.index("example.com/2")


def test_shell_load_then_find_no_results(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(INDEX))
    with patch("main.INDEX_FILE", str(index_file)), \
         patch("builtins.input", side_effect=["load", "find nonexistentword", "quit"]):
        run_shell()
    assert "no pages" in capsys.readouterr().out.lower()


def test_shell_load_then_print_word(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(INDEX))
    with patch("main.INDEX_FILE", str(index_file)), \
         patch("builtins.input", side_effect=["load", "print hello", "quit"]):
        run_shell()
    out = capsys.readouterr().out
    assert "hello" in out
    assert "http://example.com/1" in out


def test_shell_load_command_missing_file(tmp_path, capsys):
    nonexistent = str(tmp_path / "missing.json")
    with patch("main.INDEX_FILE", nonexistent), \
         patch("builtins.input", side_effect=["load", "quit"]):
        run_shell()
    assert "No index file found" in capsys.readouterr().out
