"""Tests for the indexer module, including build/load pipeline integration."""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import patch

from indexer import tokenise, build_index, STOPWORDS
from main import cmd_build, cmd_load

# ---------------------------------------------------------------------------
# Shared data for pipeline tests
# ---------------------------------------------------------------------------

PIPELINE_INDEX = {
    "_meta": {"doc_count": 1, "doc_lengths": {"http://example.com/": 3}},
    "hello": {"http://example.com/": {"frequency": 2, "positions": [0, 2]}},
    "world": {"http://example.com/": {"frequency": 1, "positions": [1]}},
}
PIPELINE_PAGES = {"http://example.com/": "hello world hello"}

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


# ---------------------------------------------------------------------------
# cmd_load
# ---------------------------------------------------------------------------

def test_cmd_load_missing_file_returns_none(capsys):
    with patch("main.os.path.exists", return_value=False):
        result = cmd_load()
    assert result is None
    assert "No index file found" in capsys.readouterr().out


def test_cmd_load_reads_index_from_file(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(PIPELINE_INDEX))
    with patch("main.INDEX_FILE", str(index_file)):
        result = cmd_load()
    assert result is not None
    assert "hello" in result
    assert "loaded" in capsys.readouterr().out.lower()


def test_cmd_load_reports_word_count(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(PIPELINE_INDEX))
    with patch("main.INDEX_FILE", str(index_file)):
        cmd_load()
    # PIPELINE_INDEX has _meta + hello + world = 3 keys
    assert "3" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# cmd_build
# ---------------------------------------------------------------------------

def test_cmd_build_calls_crawl_and_build_index(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    with patch("main.crawl", return_value=PIPELINE_PAGES) as mock_crawl, \
         patch("main.build_index", return_value=PIPELINE_INDEX) as mock_build, \
         patch("main.INDEX_FILE", str(index_file)):
        result = cmd_build()
    mock_crawl.assert_called_once()
    mock_build.assert_called_once_with(PIPELINE_PAGES)
    assert result == PIPELINE_INDEX


def test_cmd_build_saves_index_to_file(tmp_path):
    index_file = tmp_path / "index.json"
    with patch("main.crawl", return_value=PIPELINE_PAGES), \
         patch("main.build_index", return_value=PIPELINE_INDEX), \
         patch("main.INDEX_FILE", str(index_file)):
        cmd_build()
    assert json.loads(index_file.read_text()) == PIPELINE_INDEX


def test_cmd_build_prints_confirmation(tmp_path, capsys):
    index_file = tmp_path / "index.json"
    with patch("main.crawl", return_value=PIPELINE_PAGES), \
         patch("main.build_index", return_value=PIPELINE_INDEX), \
         patch("main.INDEX_FILE", str(index_file)):
        cmd_build()
    assert "saved" in capsys.readouterr().out.lower()
