# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Highlight App is a Python desktop application (tkinter GUI) that aggregates basketball highlight videos from multiple social media platforms (Twitter and YouTube). Users can search for highlights, view results in a table, and open videos by double-clicking.

## Setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Copy `.env.template` to `.env` and fill in API credentials
3. Run `uv sync` to create the virtual environment and install dependencies

## Commands

```bash
uv sync                                  # Install dependencies (creates .venv)
uv run highlight-app                     # Run the application
uv run pytest                            # Run all tests
uv run pytest tests/test_searcher.py     # Run a single test file
uv run pytest tests/test_searcher.py::TestHighlightSearcher::test_empty_searcher  # Run single test
uv add <package>                         # Add a dependency
uv add --dev <package>                   # Add a dev dependency
```

## Project Structure

```text
src/highlight_app/
├── __init__.py          # Package entry point, exposes main()
├── app.py               # HighlightApp (GUI) and HighlightSearcher classes
├── config.py            # APIKeys dataclass, load_api_keys() from .env
├── exceptions.py        # Exception hierarchy (APIError, etc.)
└── clients/
    ├── __init__.py
    ├── twitter_client.py    # TwitterClient (tweepy + scraping fallback)
    └── youtube_client.py    # YouTubeClient (Google API)
```

## Architecture

### Core Components

- **app.py**: Entry point containing two main classes:
  - `HighlightApp`: tkinter GUI window with search box and results treeview
  - `HighlightSearcher`: Aggregates results from multiple platform clients, sorts by score/date

- **config.py**: Loads API keys from `.env` file into `APIKeys` dataclass. Validates required environment variables on startup.

- **exceptions.py**: Custom exception hierarchy (`HighlightAppError` base) with API-specific errors: `APIAuthenticationError`, `RateLimitError`, `APINotAvailableError`, `SearchError`

### Platform Clients

Each client implements a `search(query: str, max_results: int) -> List[Dict]` method returning standardized results:

```python
{"platform": str, "title": str, "url": str, "upload_date": str, "score": int}
```

- **twitter_client.py**: Uses tweepy for Twitter API v1.1 with web scraping fallback
- **youtube_client.py**: Uses Google API client for YouTube Data API v3

### Key Patterns

- **Dependency injection**: `HighlightSearcher` accepts clients dict, enabling easy testing with mocks
- **Graceful degradation**: Search continues if one platform fails; errors stored in `last_error`
- **Threading**: Search runs in background thread to keep GUI responsive
- **Error hierarchy**: All API errors inherit from `APIError` for consistent handling
