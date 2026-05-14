"""Tests for the search module and CLI shell commands."""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import patch

from search import (
    best_snippet_position, extract_snippet, find_pages, get_stats,
    print_word, rank_pages, suggest,
)
from main import cmd_stats, load_pages, run_shell

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
    # "world" and "python" are both in INDEX but appear on different pages —
    # their intersection is empty, so "No pages found." should be printed.
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(INDEX))
    with patch("main.INDEX_FILE", str(index_file)), \
         patch("builtins.input", side_effect=["load", "find world python", "quit"]):
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


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------

def test_get_stats_doc_count():
    assert get_stats(INDEX)["doc_count"] == 2


def test_get_stats_word_count():
    # INDEX has _meta + hello + world + python = 3 real words
    assert get_stats(INDEX)["word_count"] == 3


def test_get_stats_total_tokens():
    assert get_stats(INDEX)["total_tokens"] == 20  # 10 + 10


def test_get_stats_avg_tokens():
    assert get_stats(INDEX)["avg_tokens"] == 10.0


def test_get_stats_top_words_sorted_by_df():
    top = get_stats(INDEX)["top_words"]
    # "hello" appears in 2 pages, "world" and "python" in 1 each
    assert top[0][0] == "hello"
    assert top[0][1] == 2


def test_get_stats_longest_page():
    url, length = get_stats(INDEX)["longest"]
    assert length == 10  # both pages are length 10, either is valid


def test_get_stats_shortest_page():
    url, length = get_stats(INDEX)["shortest"]
    assert length == 10


def test_get_stats_empty_index(capsys):
    empty = {"_meta": {"doc_count": 0, "doc_lengths": {}}}
    s = get_stats(empty)
    assert s["doc_count"] == 0
    assert s["word_count"] == 0
    assert s["total_tokens"] == 0
    assert s["avg_tokens"] == 0.0
    assert s["longest"] is None
    assert s["shortest"] is None


# ---------------------------------------------------------------------------
# cmd_stats
# ---------------------------------------------------------------------------

def test_cmd_stats_shows_page_count(capsys):
    cmd_stats(INDEX)
    assert "2" in capsys.readouterr().out


def test_cmd_stats_shows_top_words(capsys):
    cmd_stats(INDEX)
    assert "hello" in capsys.readouterr().out


def test_cmd_stats_shows_longest_shortest(capsys):
    cmd_stats(INDEX)
    out = capsys.readouterr().out
    assert "Longest" in out
    assert "Shortest" in out


# ---------------------------------------------------------------------------
# CLI shell — stopword feedback
# ---------------------------------------------------------------------------

def test_shell_find_stopword_shows_note(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(INDEX))
    with patch("main.INDEX_FILE", str(index_file)), \
         patch("builtins.input", side_effect=["load", "find the", "quit"]):
        run_shell()
    out = capsys.readouterr().out
    assert "stopword" in out.lower()
    assert "No searchable words" in out


def test_shell_find_mixed_stopword_and_real_word(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(INDEX))
    with patch("main.INDEX_FILE", str(index_file)), \
         patch("builtins.input", side_effect=["load", "find the hello", "quit"]):
        run_shell()
    out = capsys.readouterr().out
    assert "stopword" in out.lower()
    assert "http://example.com/1" in out


def test_shell_find_multiple_stopwords(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(INDEX))
    with patch("main.INDEX_FILE", str(index_file)), \
         patch("builtins.input", side_effect=["load", "find the and", "quit"]):
        run_shell()
    out = capsys.readouterr().out
    assert "are stopwords" in out


# ---------------------------------------------------------------------------
# CLI shell — stats command
# ---------------------------------------------------------------------------

def test_shell_stats_without_index(capsys):
    with patch("builtins.input", side_effect=["stats", "quit"]):
        run_shell()
    assert "no index" in capsys.readouterr().out.lower()


def test_shell_stats_with_index(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(INDEX))
    with patch("main.INDEX_FILE", str(index_file)), \
         patch("builtins.input", side_effect=["load", "stats", "quit"]):
        run_shell()
    out = capsys.readouterr().out
    assert "Index Statistics" in out
    assert "hello" in out


# ---------------------------------------------------------------------------
# suggest
# ---------------------------------------------------------------------------

def test_suggest_prefix_match():
    results = suggest(INDEX, "hell")
    assert "hello" in results


def test_suggest_edit_distance_typo():
    # "helo" is 1 edit from "hello"
    results = suggest(INDEX, "helo")
    assert "hello" in results


def test_suggest_exact_word_excluded():
    # word already in index should not suggest itself
    results = suggest(INDEX, "hello")
    assert "hello" not in results


def test_suggest_empty_string():
    assert suggest(INDEX, "") == []


def test_suggest_single_char():
    assert suggest(INDEX, "h") == []


def test_suggest_no_match():
    assert suggest(INDEX, "zzzzzzzzz") == []


def test_suggest_returns_list():
    assert isinstance(suggest(INDEX, "helo"), list)


# ---------------------------------------------------------------------------
# extract_snippet
# ---------------------------------------------------------------------------

def test_extract_snippet_middle():
    text = "the quick brown fox jumps over the lazy dog"
    # tokens: ["the","quick","brown","fox","jumps","over","the","lazy","dog"]
    # "fox" is at position 3; context=2 gives tokens[1:6]
    snippet = extract_snippet(text, 3, context=2)
    assert "fox" in snippet
    assert snippet.startswith("…")   # truncated on left
    assert snippet.endswith("…")     # truncated on right


def test_extract_snippet_at_start():
    text = "fox jumps over the lazy"
    snippet = extract_snippet(text, 0, context=2)
    assert snippet.startswith("fox")  # no leading ellipsis


def test_extract_snippet_at_end():
    text = "the quick fox"
    snippet = extract_snippet(text, 2, context=2)
    assert not snippet.endswith("…")  # no trailing ellipsis


def test_extract_snippet_position_out_of_range():
    assert extract_snippet("hello world", 100) == ""


def test_extract_snippet_empty_text():
    assert extract_snippet("", 0) == ""


# ---------------------------------------------------------------------------
# best_snippet_position
# ---------------------------------------------------------------------------

# Build a small index where "love" is at position 2 and "life" is at position 8
# on page 1 — ten tokens apart — and also at position 5 on page 1.
# The best window (context=5) containing both should anchor on "love" at 2
# because the window [0..7] covers both position 2 (love) and position 5 (life).
_BSP_INDEX = {
    "_meta": {"doc_count": 1, "doc_lengths": {"http://p1/": 15}},
    "love": {"http://p1/": {"frequency": 1, "positions": [2]}},
    "life": {"http://p1/": {"frequency": 2, "positions": [5, 12]}},
}


def test_best_snippet_position_prefers_window_covering_both_words():
    pos = best_snippet_position(_BSP_INDEX, ["love", "life"], "http://p1/", context=5)
    # position 2 anchors a window [0..7] containing both love(2) and life(5)
    assert pos == 2


def test_best_snippet_position_single_word():
    pos = best_snippet_position(_BSP_INDEX, ["love"], "http://p1/", context=5)
    assert pos == 2


def test_best_snippet_position_word_not_in_url():
    pos = best_snippet_position(_BSP_INDEX, ["love"], "http://missing/", context=5)
    assert pos == 0


def test_best_snippet_position_empty_words():
    pos = best_snippet_position(_BSP_INDEX, [], "http://p1/", context=5)
    assert pos == 0


# ---------------------------------------------------------------------------
# load_pages
# ---------------------------------------------------------------------------

def test_load_pages_returns_none_when_missing(tmp_path):
    with patch("main.PAGES_FILE", str(tmp_path / "missing.json")):
        assert load_pages() is None


def test_load_pages_returns_dict_when_present(tmp_path):
    pages_file = tmp_path / "pages.json"
    pages_file.write_text(json.dumps({"http://example.com/": "hello world"}))
    with patch("main.PAGES_FILE", str(pages_file)):
        result = load_pages()
    assert result == {"http://example.com/": "hello world"}


# ---------------------------------------------------------------------------
# CLI shell — print with suggestions
# ---------------------------------------------------------------------------

def test_shell_print_unknown_word_shows_suggestion(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(INDEX))
    with patch("main.INDEX_FILE", str(index_file)), \
         patch("builtins.input", side_effect=["load", "print helo", "quit"]):
        run_shell()
    out = capsys.readouterr().out
    assert "Did you mean" in out
    assert "hello" in out


def test_shell_print_known_word_no_suggestion(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(INDEX))
    with patch("main.INDEX_FILE", str(index_file)), \
         patch("builtins.input", side_effect=["load", "print hello", "quit"]):
        run_shell()
    assert "Did you mean" not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# CLI shell — find with suggestions
# ---------------------------------------------------------------------------

def test_shell_find_unknown_word_shows_suggestion(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(INDEX))
    with patch("main.INDEX_FILE", str(index_file)), \
         patch("builtins.input", side_effect=["load", "find helo", "quit"]):
        run_shell()
    out = capsys.readouterr().out
    assert "Did you mean" in out
    assert "hello" in out


def test_shell_find_completely_unknown_no_suggestion(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(INDEX))
    with patch("main.INDEX_FILE", str(index_file)), \
         patch("builtins.input", side_effect=["load", "find zzzzzzzzz", "quit"]):
        run_shell()
    out = capsys.readouterr().out
    assert "not in index" in out
    assert "Did you mean" not in out


# ---------------------------------------------------------------------------
# CLI shell — find with snippets
# ---------------------------------------------------------------------------

PAGES = {
    "http://example.com/1": "the hello world and hello again",
    "http://example.com/2": "the hello python is great",
}


def test_shell_find_shows_snippet_when_pages_loaded(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    pages_file = tmp_path / "pages.json"
    index_file.write_text(json.dumps(INDEX))
    pages_file.write_text(json.dumps(PAGES))
    with patch("main.INDEX_FILE", str(index_file)), \
         patch("main.PAGES_FILE", str(pages_file)), \
         patch("builtins.input", side_effect=["load", "find hello", "quit"]):
        run_shell()
    out = capsys.readouterr().out
    assert '"' in out  # snippet is wrapped in quotes


def test_shell_find_no_snippet_without_pages(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(INDEX))
    with patch("main.INDEX_FILE", str(index_file)), \
         patch("main.PAGES_FILE", str(tmp_path / "missing.json")), \
         patch("builtins.input", side_effect=["load", "find hello", "quit"]):
        run_shell()
    # Results still shown, just no snippet lines
    out = capsys.readouterr().out
    assert "http://example.com/1" in out
