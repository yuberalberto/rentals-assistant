# Rentals Assistant

An automated rental-listing pipeline that scrapes 9+ sources, filters and scores apartments against a detailed profile, and sends tiered Telegram alerts — so you never miss a good deal in a competitive market.

---

## Quick Start

### Requirements

- Python >= 3.14
- A Telegram bot token (from [@BotFather](https://t.me/botfather))
- Your Telegram chat ID (message the bot, then ask [@userinfobot](https://t.me/userinfobot))
- See [docs/telegram-setup.md](docs/telegram-setup.md) for a step-by-step guide

### Install

```bash
git clone https://github.com/yourusername/rentals-assistant.git
cd rentals-assistant

# Using uv (recommended) — creates a local .venv/ from uv.lock
uv sync

# Or pip — creates a local virtualenv manually
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Configure

```bash
cp .env.example .env
# Edit .env and fill in TELEGRAM_TOKEN and TELEGRAM_CHAT_ID
# (see docs/telegram-setup.md if you don't have them yet)
```

### Run

```bash
# Start the scheduler (scrapes at 08:00, 13:00, and 18:00 EST)
python -m rentals_assistant

# Or run a single manual scan
python -c "from rentals_assistant.pipeline import run; run(scrapers, store, notifier)"
```

---

## How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Scrapers   │ ──> │ Hard Filters│ ──> │   Scorer    │ ──> │  Notifier   │
│  (9+ sites) │     │ (must-haves)│     │ (0-4 pts)   │     │  (Telegram) │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                                          │
       └──────────────────────────────────────────┘
                          SQLite deduplication
```

1. **Scrape** — Fetches listings from 9+ rental platforms concurrently.
2. **Filter** — Rejects listings that fail hard requirements (price, bedrooms, pets, laundry, etc.).
3. **Score** — Assigns 0–4 points on soft preferences (utilities, floor level, parking, outdoor space).
4. **Dedupe** — Persists listings to SQLite; only *new* matches trigger alerts.
5. **Notify** — Sends tiered Telegram messages: Perfect, Strong, or Check it.

---

## Data Sources

| Source | Method | Notes |
|---|---|---|
| [Rentals.ca](https://rentals.ca) | `httpx` + BeautifulSoup | Static HTML, broad coverage |
| [Kijiji](https://kijiji.ca) | Playwright | JS-rendered, no login required |
| [PadMapper](https://padmapper.com) | `httpx` + BeautifulSoup | Aggregates Kijiji — deduped by canonical URL |
| [Zumper](https://zumper.com) | `httpx` + JSON API | API-like responses |
| [ViewIt.ca](https://viewit.ca) | `httpx` + BeautifulSoup | Strong Ontario inventory |
| [Craigslist](https://hamilton.craigslist.org) | RSS feed | Zero-maintenance RSS parser |
| [liv.rent](https://liv.rent) | `httpx` + BeautifulSoup | Modern landlords, different pool |
| [Wilson Blanchard](https://wilsonblanchard.com) | `httpx` + BeautifulSoup | Major KW property manager |
| [Activa](https://activa.ca) | `httpx` + BeautifulSoup | Large KW developer/manager |

---

## Technical Deep Dive

> For the curious, future teammates, or anyone reading this on a portfolio screen.

### Architecture

The project follows a clean, modular pipeline design:

- `rentals_assistant/pipeline.py` — Async orchestrator. Calls all scrapers concurrently, handles failures gracefully (logs and skips), wires filter → score → store → notify.
- `rentals_assistant/filters.py` — Pure boolean functions. Hard filters never crash on missing data: `unknown` means "let it through to scoring".
- `rentals_assistant/scorer.py` — Soft scoring engine. Assigns 0–4 points and a tier (`perfect` / `strong` / `check`). Cambridge / South Kitchener proximity gets a flag (not a point).
- `rentals_assistant/store.py` — SQLite CRUD with `sqlite3` (stdlib). `is_new()` + `mark_notified()` prevent duplicate alerts across runs. Rejected listings are still persisted (`tier=None`, `notified=0`) for audit.
- `rentals_assistant/notifier.py` — Telegram formatter + sender via `httpx`. Emojis and tier labels make alerts scannable on mobile.
- `rentals_assistant/scheduler.py` — APScheduler with 3 cron triggers (08:00, 13:00, 18:00) in `America/Toronto`. Timezone is configurable.
- `rentals_assistant/config.py` — `pydantic-settings` loading from `.env`. Raises a clear `ConfigError` if required keys are missing.

### Data Model (SQLite)

```text
listings
├── id               TEXT PRIMARY KEY  -- sha256(source + external_id)
├── source           TEXT
├── external_id      TEXT
├── url              TEXT
├── title            TEXT
├── price_cad        INTEGER
├── utilities        TEXT  -- "included" | "extra" | "unknown"
├── bedrooms         INTEGER
├── city             TEXT
├── floor_level      TEXT  -- "upper" | "main" | "basement" | "unknown"
├── laundry_inunit   INTEGER  -- 1 | 0 | NULL
├── outdoor_space    INTEGER  -- 1 | 0 | NULL
├── parking_spots    INTEGER
├── pets             TEXT  -- "cats_confirmed" | "allowed" | "not_allowed" | "unknown"
├── score            INTEGER  -- 0-4
├── tier             TEXT  -- "perfect" | "strong" | "check" | NULL
├── first_seen       DATETIME
├── last_seen        DATETIME
└── notified         INTEGER  -- 0 | 1
```

### Filter Logic

Hard filters (must pass all):

| Rule | Value |
|---|---|
| Price ceiling | ≤ $2,000 CAD |
| Bedrooms | Exactly 2 |
| Floor level | Not basement |
| Pets | Not `not_allowed` (cats must be confirmed or generic `allowed`) |
| Laundry | In-unit only (when known) |
| Parking | ≥ 1 spot (when known) |

Soft scoring (0–4 points):

| Criterion | Points |
|---|---|
| Utilities included | +1 |
| Upper floor | +1 |
| Outdoor space (balcony/yard) | +1 |
| Parking ≥ 2 spots | +1 |

Tier mapping:

| Score | Tier | Emoji |
|---|---|---|
| 4 | Perfect | 🟢 |
| 2–3 | Strong | 🟡 |
| 0–1 | Check it | 🔵 |

### Project Structure

```text
rentals-assistant/
├── rentals_assistant/
│   ├── __init__.py
│   ├── __main__.py          # Entry point: starts the scheduler
│   ├── config.py            # pydantic-settings + env validation
│   ├── filters.py           # Hard filter engine
│   ├── models.py            # RawListing dataclass
│   ├── notifier.py          # Telegram formatter + sender
│   ├── pipeline.py          # Async orchestrator
│   ├── scheduler.py         # APScheduler cron jobs
│   ├── scorer.py            # Soft scoring engine
│   ├── store.py             # SQLite deduplication layer
│   └── scrapers/
│       ├── base.py          # Abstract Scraper(ABC)
│       ├── activa.py
│       ├── craigslist.py
│       ├── kijiji.py
│       ├── liv_rent.py
│       ├── padmapper.py
│       ├── rentals_ca.py
│       ├── viewit.py
│       ├── wilson_blanchard.py
│       └── zumper.py
├── tests/
│   ├── scrapers/            # HTML/JSON fixtures + per-scraper tests
│   ├── test_config.py
│   ├── test_filters.py
│   ├── test_pipeline.py
│   ├── test_scorer.py
│   ├── test_store.py
│   └── test_scheduler.py
├── pyproject.toml
├── .env.example
└── README.md
```

### Testing

```bash
# Fast unit tests (no network)
pytest -m "not integration"

# Full suite including live scraper tests
pytest

# With coverage
pytest --cov=rentals_assistant --cov-report=term-missing
```

---

## License

MIT
