# Rentals Scraper — Automated Apartment Search

## 1. Problem
A couple in KW paying $2,800/month ($2,300 rent + $500 utilities) at Highland @ Ira Needles
needs to reduce housing costs by at least $800/month without leaving the region — both work
in Cambridge and Ayr. Manual monitoring of rental sites is too slow for a competitive market.

## 2. What
A Python pipeline that scrapes 5 rental platforms 3× per day, scores and filters listings
against a detailed client profile, deduplicates against SQLite, and sends tiered Telegram
alerts — ranked by how closely the listing matches the profile, not just binary pass/fail.

## 3. Client Profile

| Attribute | Value | Type |
|---|---|---|
| Occupants | Couple | — |
| Pets | 2 cats (not negotiable) | Hard filter |
| Bedrooms | 2BR | Hard filter |
| Price ceiling | $2,000/month | Hard filter |
| Basement units | Never | Hard filter |
| Laundry | In-unit only | Hard filter |
| Parking | 1 spot min — 2nd spot availability is nice-to-have | Hard (1) / Soft (2nd) |
| Price floor | $1,400/month | Soft (below = flag as suspicious) |
| Utilities included | Strongly preferred | Soft — ★ flag |
| Floor level | Upper floors preferred | Soft — 🏢 flag |
| Outdoor space | Balcony or yard | Soft — 🌿 flag |
| Proximity | Cambridge / South Kitchener (near Ayr) | Soft — 📍 flag |

**Context:** Currently mes-a-mes — can move anytime. Every month in current place = $800
extra. Urgency is real even without a hard deadline.

**Critical distinction on pets:** Many KW listings say "pets allowed" but mean one small dog.
The scraper must differentiate: `cats_confirmed` (listing explicitly says cats OK),
`pets_allowed` (generic), `pets_not_allowed`. Only `pets_allowed` or `cats_confirmed` pass.

## 4. How

### Alert tiers (what goes to Telegram)

Listings that pass all hard filters are scored 0–4 on soft criteria and tiered:

| Tier | Score | Label |
|---|---|---|
| PERFECT | 4 | 🟢 Perfect match |
| STRONG | 2–3 | 🟡 Strong match |
| CHECK | 0–1 | 🔵 Check it |

Listing is **discarded silently** only if it fails a hard filter. Otherwise it always
gets sent — even a CHECK tier listing may be worth a call.

### Alert format (Telegram)
```
🟢 Perfect match — Kijiji
2BR · $1,850/mo ★ utilities incl.
Cambridge, ON · Upper floor 🏢 · Balcony 🌿 · 2 parking 🚗
Cats: confirmed 🐱
https://kijiji.ca/...
```

### Sources and fetch strategy
| Source | Method | Notes |
|---|---|---|
| Rentals.ca | httpx + BeautifulSoup | Static HTML |
| Kijiji | Playwright | JS-rendered, login not required |
| PadMapper | httpx + BeautifulSoup | Aggregates Kijiji — deduplicate by canonical URL |
| Zumper | httpx + BeautifulSoup | API-like JSON response |
| ViewIt.ca | httpx + BeautifulSoup | Strong Ontario inventory, KW-specific listings |
| Craigslist (Hamilton) | httpx + RSS feed | Covers KW area — trivial, zero maintenance |
| liv.rent | httpx + BeautifulSoup | Growing Ontario pool, modern landlords, different inventory |
| Wilson Blanchard | httpx + BeautifulSoup | Major KW property manager — posts before aggregators |
| Activa | httpx + BeautifulSoup | Large KW developer/manager — direct listings |
| Regional Properties | httpx + BeautifulSoup | KW-area direct landlord — URL TBD at implementation |
| Facebook Marketplace | Playwright | ToS risk — disabled by default, isolated module |

### Data model (SQLite — `listings` table)
```
id               TEXT PRIMARY KEY   -- sha256(source + external_id)
source           TEXT               -- "kijiji" | "rentals_ca" | ...
external_id      TEXT
url              TEXT
title            TEXT
price_cad        INTEGER
utilities        TEXT               -- "included" | "extra" | "unknown"
bedrooms         INTEGER
city             TEXT
floor_level      TEXT               -- "upper" | "main" | "basement" | "unknown"
laundry_inunit   INTEGER            -- 1 | 0 | NULL (unknown)
outdoor_space    INTEGER            -- 1 | 0 | NULL (unknown)
parking_spots    INTEGER            -- 1 | 2 | NULL (unknown)
pets             TEXT               -- "cats_confirmed" | "allowed" | "not_allowed" | "unknown"
score            INTEGER            -- 0–4 computed from soft filters
tier             TEXT               -- "perfect" | "strong" | "check"
first_seen       DATETIME
last_seen        DATETIME
notified         INTEGER            -- 0 | 1
```

### Module layout
```
rentals_assistant/
├── scrapers/
│   ├── base.py               # Abstract Scraper(ABC): fetch() → list[RawListing]
│   ├── rentals_ca.py
│   ├── kijiji.py
│   ├── padmapper.py
│   ├── zumper.py
│   ├── viewit.py
│   ├── craigslist.py         # RSS feed parser — no Playwright needed
│   ├── liv_rent.py
│   ├── pm_wilson_blanchard.py
│   ├── pm_activa.py
│   ├── pm_regional.py
│   └── facebook.py           # Disabled by default via ENABLE_FACEBOOK=false
├── pipeline.py          # Orchestrator: scrape → filter → score → dedupe → alert
├── filters.py           # Hard filters — returns bool
├── scorer.py            # Soft scoring — returns (score: int, flags: list[str])
├── store.py             # SQLite CRUD via sqlite3 (stdlib)
├── notifier.py          # python-telegram-bot: send_alert(listing)
├── scheduler.py         # APScheduler: 3× daily cron triggers
└── config.py            # pydantic-settings: env vars with validation
```

### Dependencies
```
httpx
playwright
beautifulsoup4
python-telegram-bot
APScheduler
pydantic-settings
```

### Config (.env)
```
TELEGRAM_TOKEN=           # from @BotFather
TELEGRAM_CHAT_ID=         # from @userinfobot after messaging the bot
PRICE_MIN=1400
PRICE_MAX=2000
ENABLE_FACEBOOK=false
LOG_LEVEL=INFO
TZ=America/Toronto
```

## 5. Tasks

### TASK-001: Project setup
**Goal:** Repo structure, dependencies, config validation
**Acceptance criteria:**
- [x] `pyproject.toml` with all dependencies pinned
- [x] `config.py` loads and validates env vars; raises on missing required keys
- [x] `pytest` runs with 0 failures on an empty test suite
- [x] `.env.example` committed with all keys, no real values
**Depends on:** none

### TASK-002: Store layer
**Goal:** SQLite CRUD + deduplication logic
**Acceptance criteria:**
- [x] `store.py` creates `listings.db` on first run with full schema
- [x] `is_new(listing_id)` returns True for unseen, False for seen
- [x] `mark_notified(listing_id)` persists correctly
- [x] Unit tests cover insert, dedup, mark_notified, and score persistence
**Depends on:** TASK-001

### TASK-003: Hard filter engine
**Goal:** Pure functions that reject listings failing any must-have
**Acceptance criteria:**
- [x] Rejects if `price_cad > 2000`
- [x] Rejects if `bedrooms != 2`
- [x] Rejects if `floor_level == "basement"`
- [x] Rejects if `pets == "not_allowed"`
- [x] Rejects if `laundry_inunit == False`
- [x] Rejects if `parking_spots < 1` (when known)
- [x] Passes if any unknown field — unknown is not a rejection, it's a CHECK tier
- [x] 100% branch coverage via unit tests
**Depends on:** TASK-001

### TASK-004: Soft scorer
**Goal:** Score 0–4 on soft criteria; assign tier label
**Acceptance criteria:**
- [x] +1 if `utilities == "included"`
- [x] +1 if `floor_level == "upper"`
- [x] +1 if `outdoor_space == True`
- [x] +1 if `parking_spots >= 2` or second spot available
- [x] Tier assignment: 4=perfect, 2-3=strong, 0-1=check
- [x] Cambridge / South Kitchener listings get `📍` flag (not a score point)
- [x] Unit tests cover all score combinations
**Depends on:** TASK-001

### TASK-005: Telegram notifier
**Goal:** Send tiered, formatted alert to Telegram
**Acceptance criteria:**
- [x] Alert includes tier emoji, source, price, utilities flag, city, soft flags, pets status, URL
- [x] `ConfigError` raised (not crash) if token or chat_id missing
- [x] Integration test sends real message to test chat
**Depends on:** TASK-001

### TASK-006: Rentals.ca scraper
**Goal:** httpx scraper returning normalized `RawListing` objects
**Acceptance criteria:**
- [x] Fetches listings for Kitchener, Waterloo, Cambridge
- [x] Extracts: price, bedrooms, utilities hint, city, floor level hint, pets hint, URL, title
- [x] Unit test uses a recorded HTML fixture (no live requests)
**Depends on:** TASK-001

### TASK-007: Kijiji scraper
**Goal:** Playwright scraper for Kijiji apartments section
**Acceptance criteria:**
- [x] Launches headless Chromium, scrapes first 2 pages per city
- [x] Extracts same fields as TASK-006 plus free-text body for cats/parking/laundry parsing
- [x] Integration test runs against live site and returns ≥ 1 result
**Depends on:** TASK-001

### TASK-008: PadMapper + Zumper scrapers
**Goal:** httpx scrapers for remaining static sources
**Acceptance criteria:**
- [x] Each returns normalized `RawListing` list
- [x] URL-based dedup removes PadMapper listings that duplicate Kijiji originals
- [x] Unit tests use HTML/JSON fixtures
**Depends on:** TASK-001

### TASK-008b: ViewIt.ca + Craigslist scrapers
**Goal:** ViewIt.ca httpx scraper and Craigslist RSS parser for Hamilton area
**Acceptance criteria:**
- [x] ViewIt.ca scraper fetches KW/Cambridge listings and returns normalized `RawListing`
- [x] Craigslist parser consumes `https://hamilton.craigslist.org/search/apa?format=rss` feed
- [x] Both use fixtures for unit tests
- [x] Craigslist parser handles malformed or missing RSS fields gracefully
**Depends on:** TASK-001

### TASK-008c: liv.rent scraper
**Goal:** httpx scraper for liv.rent Ontario listings
**Acceptance criteria:**
- [x] Fetches Kitchener, Waterloo, Cambridge results
- [x] Extracts price, bedrooms, pets policy, utilities hint, URL, city
- [x] Unit test uses HTML fixture
**Depends on:** TASK-001

### TASK-008d: KW property management scrapers
**Goal:** Direct scrapers for Activa and KW Property (rhenti.com white-label)
**Acceptance criteria:**
- [x] Each scraper has its base URL confirmed and documented in a comment
  - Activa: `https://activa.ca/whats-available/?post_types=rental`
  - KW Property: `https://api.rhenti.com/properties` (white-label ID `6931f6f3cd23c75167f8dd66`)
- [x] Returns normalized `RawListing` — missing fields set to `None`, not error
- [x] If a PM site returns 0 listings, logs a warning (site may have changed structure)
- [x] Unit tests use fixtures; URLs confirmed before fixtures are recorded
**Depends on:** TASK-001

### TASK-009: Pipeline orchestrator ✅
**Goal:** Wire scrape → hard filter → score → dedupe → notify
**Acceptance criteria:**
- [x] `pipeline.run()` calls all enabled scrapers
- [x] Hard-filtered listings are stored as `notified=0, tier=null` (for audit)
- [x] Only new + passing listings trigger Telegram notification
- [x] Scraper failure logs error and continues — never aborts the full run
- [x] End-to-end integration test with mocked notifier passes
**Implementation:** `rentals_assistant/pipeline.py` — `make_listing_id()` + `run()` async orchestrator. `_listing_to_record()` helper avoids field duplication. `mark_notified()` gated on `notifier()` return value — failed Telegram sends are retried on next run. 12 unit tests, all passing.
**Depends on:** TASK-002, TASK-003, TASK-004, TASK-005, TASK-006, TASK-007, TASK-008, TASK-008b, TASK-008c, TASK-008d

### TASK-010: Scheduler ✅
**Goal:** APScheduler cron triggers at 08:00 / 13:00 / 18:00 EST
**Acceptance criteria:**
- [x] `scheduler.py start()` registers 3 cron jobs
- [x] `TZ=America/Toronto` respected
- [x] `python -m rentals_assistant` starts scheduler and logs next fire time
**Implementation:** `rentals_assistant/scheduler.py` — `build_scheduler(config, scrapers, store, notifier)` creates `AsyncIOScheduler` with `config.tz`, registers 3 `CronTrigger` jobs (08:00, 13:00, 18:00), each calling an async `_run_pipeline()` wrapper that awaits `pipeline.run()`. `log_next_fire_times()` logs `job.next_run_time` for every job. `start()` is the integration entry point: loads config, builds `Store("listings.db")`, uses `send_alert` as notifier, wires everything via `build_scheduler()`, starts the scheduler, and blocks with `asyncio.get_event_loop().run_forever()`. `__main__.py` simply imports `start()` so `python -m rentals_assistant` works. 6 unit tests cover job count, hours set, timezone (default and override), pipeline call, and fire-time logging. 446 passed, 0 regressions.
**Depends on:** TASK-009

### TASK-011: Telegram bot setup guide ✅
**Goal:** Runbook for @BotFather setup and getting chat_id
**Acceptance criteria:**
- [x] `docs/telegram-setup.md` documents all steps end-to-end
- [x] Covers how to get chat_id after messaging the bot
**Implementation:** `docs/telegram-setup.md` — step-by-step guide covering prerequisites, creating a bot via @BotFather (`/newbot`), obtaining `chat_id` via @userinfobot, configuring `.env` with `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID`, validation via `curl` smoke test and `tests/test_notifier.py`, and a troubleshooting section for the 3 most common errors (unauthorized token, chat not found, bad format). `tests/test_docs.py` verifies the doc exists, contains all required keywords (`BotFather`, `chat_id`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `.env`), and includes a validation step. 3 tests pass. Full suite: 449 passed, 0 regressions.
**Depends on:** TASK-005

### TASK-012: Telegram manual trigger ✅
**Goal:** `/run` command via Telegram dispatches the pipeline on-demand
**Acceptance criteria:**
- [x] `bot.py` starts a polling loop using the same token as the notifier
- [x] `/run` command is rejected (silent ignore) if sender `chat_id != TELEGRAM_CHAT_ID`
- [x] Authorized `/run` responds immediately with "Scanning... 🔍" before pipeline starts
- [x] After pipeline completes, results are sent via the normal notifier flow
- [x] `python -m rentals_assistant --bot` starts the bot (scheduler excluded for now)
- [x] If pipeline is already running, responds "Already scanning, please wait ⏳" (no double-run)
- [x] Unit test: unauthorized chat_id is ignored; authorized chat_id triggers pipeline mock
**Implementation:** `rentals_assistant/bot.py` — `python-telegram-bot` v20+ async polling. `_handle_run(update, context)` checks `update.effective_chat.id == int(config.telegram_chat_id)`; unauthorized senders are silently ignored. `_pipeline_lock` (module-level `asyncio.Lock`) prevents double-run — if locked, replies "Already scanning, please wait ⏳". Authorized calls reply "Scanning... 🔍", then `async with _pipeline_lock:` awaits `pipeline.run(scrapers=[], store=Store("listings.db"), notifier=send_alert)`. `build_application(token)` wires `CommandHandler("run", _handle_run)`. `start_bot()` loads config and calls `build_application(...).run_polling()`. `rentals_assistant/__main__.py` — `--bot` CLI flag dispatches to `start_bot()`, otherwise runs scheduler (`start()`). `tests/test_bot.py` — 4 tests: unauthorized ignore, authorized trigger, double-run busy, and `build_application` handler wiring. 453 passed, 1 skipped, 0 regressions.
**Depends on:** TASK-009, TASK-010, TASK-011
