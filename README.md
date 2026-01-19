# Highlight App

Basketball highlights aggregator with a Tkinter GUI that searches Twitter and YouTube APIs for highlight videos.

## Requirements

- Python 3.10+
- System-level `python3-tk` package (not pip-installable)
- API keys for Twitter and YouTube (see [Configuration](#configuration))

## Installation

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/your-username/Highlight-App.git
cd Highlight-App
uv sync
```

## Configuration

Copy `.env.template` to `.env` and fill in your API keys:

```bash
cp .env.template .env
```

Required API keys:
- **Twitter**: API key, secret, access token, and access token secret (requires elevated access for search)
- **YouTube**: Google API key with YouTube Data API v3 enabled

## Usage

```bash
uv run highlight-app
```

Enter a search query (e.g., player name, team, game) and click Search. Results are aggregated from Twitter and YouTube, sorted by relevance score.

## Development

```bash
# Install dev dependencies
uv sync

# Run linter
uv run ruff check src/ tests/

# Format code
uv run ruff format src/ tests/

# Type check
uv run ty check src/ tests/

# Run tests
uv run pytest tests/
```

## Project Structure

```
src/highlight_app/
├── app.py           # Main GUI and search aggregator
├── config.py        # API key loading from .env
├── exceptions.py    # Custom exception hierarchy
└── clients/
    ├── twitter_client.py  # Twitter API client
    └── youtube_client.py  # YouTube API client
```

## API Notes

- **Twitter**: Free tier returns 403 errors; falls back to scraping (unreliable)
- **YouTube**: 10,000 units/day quota; each search costs 100 units

## License

MIT
