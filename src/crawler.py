"""Web crawler for quotes.toscrape.com.

Performs a breadth-first crawl of a website, respecting a politeness
window of at least 6 seconds between successive HTTP requests.
"""

import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

POLITENESS_DELAY = 6  # seconds between requests


def crawl(start_url: str) -> dict[str, str]:
    """Crawl all pages reachable from start_url on the same domain.

    Returns a dict mapping each visited URL to its plain-text content.
    Skips external links and avoids revisiting URLs.
    """
    visited: set[str] = set()
    queue: list[str] = [start_url]
    pages: dict[str, str] = {}
    base_domain = urlparse(start_url).netloc

    while queue:
        url = queue.pop(0)
        if url in visited:
            continue

        # Sleep before every request except the first, ensuring the
        # politeness window applies only between actual HTTP requests.
        if visited:
            time.sleep(POLITENESS_DELAY)

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"  [error] Could not fetch {url}: {e}")
            visited.add(url)
            continue

        visited.add(url)
        soup = BeautifulSoup(response.text, "html.parser")

        pages[url] = soup.get_text(separator=" ")

        for tag in soup.find_all("a", href=True):
            link = urljoin(url, tag["href"])
            parsed = urlparse(link)
            # Strip fragment and query to avoid duplicate pages
            clean = parsed._replace(fragment="", query="").geturl()
            if parsed.netloc == base_domain and clean not in visited:
                queue.append(clean)

        print(f"  Crawled ({len(pages)}): {url}")

    return pages
