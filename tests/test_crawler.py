"""Tests for the web crawler module."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import Mock, patch

import requests as req

from crawler import crawl, POLITENESS_DELAY

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SIMPLE_HTML = """
<html><body>
  <p>Hello world</p>
  <a href="/page2">Page 2</a>
</body></html>
"""

PAGE2_HTML = """
<html><body>
  <p>Another page with content</p>
</body></html>
"""


def mock_response(html: str, status: int = 200) -> Mock:
    m = Mock()
    m.text = html
    m.status_code = status
    m.raise_for_status = Mock()
    return m


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@patch("crawler.time.sleep")
@patch("crawler.requests.get")
def test_crawl_returns_start_page(mock_get, mock_sleep):
    mock_get.return_value = mock_response("<html><body><p>Test content</p></body></html>")
    pages = crawl("http://example.com/")
    assert "http://example.com/" in pages
    assert "Test" in pages["http://example.com/"]


@patch("crawler.time.sleep")
@patch("crawler.requests.get")
def test_crawl_follows_internal_links(mock_get, mock_sleep):
    mock_get.side_effect = [
        mock_response(SIMPLE_HTML),
        mock_response(PAGE2_HTML),
    ]
    pages = crawl("http://example.com/")
    assert len(pages) == 2
    assert "http://example.com/page2" in pages


@patch("crawler.time.sleep")
@patch("crawler.requests.get")
def test_crawl_ignores_external_links(mock_get, mock_sleep):
    html = '<html><body><a href="http://other.com/page">external</a></body></html>'
    mock_get.return_value = mock_response(html)
    pages = crawl("http://example.com/")
    assert len(pages) == 1


@patch("crawler.time.sleep")
@patch("crawler.requests.get")
def test_crawl_no_duplicate_pages(mock_get, mock_sleep):
    html = '<html><body><a href="/">home</a><a href="/">home again</a></body></html>'
    mock_get.return_value = mock_response(html)
    pages = crawl("http://example.com/")
    assert len(pages) == 1


@patch("crawler.time.sleep")
@patch("crawler.requests.get")
def test_crawl_handles_request_error_gracefully(mock_get, mock_sleep):
    mock_get.side_effect = req.RequestException("Connection refused")
    pages = crawl("http://example.com/")
    assert pages == {}


@patch("crawler.time.sleep")
@patch("crawler.requests.get")
def test_crawl_sleeps_between_requests(mock_get, mock_sleep):
    mock_get.side_effect = [
        mock_response(SIMPLE_HTML),
        mock_response(PAGE2_HTML),
    ]
    crawl("http://example.com/")
    # sleep must be called at least once between the two requests
    assert mock_sleep.call_count >= 1
    mock_sleep.assert_called_with(POLITENESS_DELAY)


@patch("crawler.time.sleep")
@patch("crawler.requests.get")
def test_crawl_skips_url_queued_twice(mock_get, mock_sleep):
    # page1 links to page2 AND page3
    # page2 also links to page3 — so page3 enters the queue twice
    # before it is visited; the second dequeue must be skipped (line 30)
    page1 = '<html><body><a href="/page2">p2</a><a href="/page3">p3</a></body></html>'
    page2 = '<html><body><a href="/page3">p3 again</a></body></html>'
    page3 = '<html><body><p>Final</p></body></html>'
    mock_get.side_effect = [
        mock_response(page1),
        mock_response(page2),
        mock_response(page3),
    ]
    pages = crawl("http://example.com/")
    assert len(pages) == 3
    # page3 must only be fetched once despite being queued twice
    assert mock_get.call_count == 3
    # 3 sleeps: queue is non-empty after each of the 3 real fetches
    assert mock_sleep.call_count == 3
