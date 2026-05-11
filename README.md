# Search Engine Tool — COMP3011 Coursework 2

A command-line search engine that crawls [quotes.toscrape.com](https://quotes.toscrape.com/), builds an inverted index, and lets you search for pages by keyword.

---

## Project Structure

```
web_crawler/
├── src/
│   ├── crawler.py   – BFS web crawler with 6-second politeness window
│   ├── indexer.py   – inverted index builder (frequency + positions)
│   ├── search.py    – print and find query logic
│   └── main.py      – interactive command-line shell
├── tests/
│   ├── test_crawler.py
│   ├── test_indexer.py
│   └── test_search.py
├── data/            – index file saved here after build
├── requirements.txt
└── README.md
```

---

## Installation

1. **Clone the repository**

   ```bash
   git clone <repo-url>
   cd web_crawler
   ```

2. **Create and activate a virtual environment** (recommended)

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

Start the shell from the repository root:

```bash
python src/main.py
```

### Commands

| Command | Description |
|---|---|
| `build` | Crawl the website, build the index, and save it to `data/index.json` |
| `load` | Load a previously saved index from `data/index.json` |
| `print <word>` | Print the full index entry (frequency + positions) for a word |
| `find <word> [word ...]` | List all pages containing every supplied word |
| `help` | Show available commands |
| `quit` | Exit the shell |

### Examples

```
> build
Starting crawl of https://quotes.toscrape.com/ ...
  Crawled (1): https://quotes.toscrape.com/
  ...
Index saved to data/index.json  (1842 unique words).

> load
Index loaded from data/index.json  (1842 unique words).

> print life
  'life' appears in 8 page(s):

  URL       : https://quotes.toscrape.com/
  Frequency : 3
  Positions : [42, 198, 310]
  ...

> find good friends
  Found 2 page(s):
    https://quotes.toscrape.com/page/2/
    https://quotes.toscrape.com/tag/friendship/

> find nonexistentword
  No pages found.
```

---

## Running the Tests

```bash
pytest tests/ -v
```

To see coverage:

```bash
pip install pytest-cov
pytest tests/ --cov=src --cov-report=term-missing
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | HTTP requests during crawling |
| `beautifulsoup4` | HTML parsing |
| `pytest` | Test framework |
