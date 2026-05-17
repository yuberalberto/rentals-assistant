# Production Hardening

## 1. Problem

The pipeline is functionally complete but unreliable for daily use: scrapers fail silently with no retry, HTTP 403s block two sources, the sync notifier blocks the async event loop, scrapers run sequentially wasting time, and there is zero visibility into run results.

## 2. What

Harden the pipeline for unattended daily operation by adding resilient HTTP handling (retry + realistic headers), converting the notifier to async, running scrapers concurrently, configuring logging, and sending a run summary to Telegram after each execution.

## 3. How

- **Shared HTTP client factory** (`rentals_assistant/http.py`): returns a pre-configured `httpx.AsyncClient` with realistic browser User-Agent rotation, retry on transient errors (5xx, timeouts), exponential backoff with jitter, and a helper for inter-request delays. No new external dependencies — retry is a simple async loop.
- **Async notifier**: convert `send_alert()` to `async def`, use `httpx.AsyncClient`.
- **Concurrent execution**: replace the sequential for-loop in `pipeline.run()` with `asyncio.gather` bounded by a configurable semaphore.
- **Run summary**: `pipeline.run()` returns a `RunResult` dataclass; a new `send_summary()` function formats and sends it to Telegram when failures occur.
- **Logging**: apply `config.log_level` at startup in `__main__.py`.

Key files affected:
- New: `rentals_assistant/http.py`
- Modified: `rentals_assistant/pipeline.py`, `rentals_assistant/notifier.py`, `rentals_assistant/__main__.py`, `rentals_assistant/config.py`, all 9 scraper files

## 4. Tasks

### TASK-100: Configure logging at entry point

**Goal:** Apply `config.log_level` so all logger output is visible with timestamps.

**Acceptance criteria:**
- [x] New `configure_logging(level: str)` helper exists and is unit-tested
- [x] `__main__.py` calls it before starting scheduler or bot
- [x] Default output format: `%(asctime)s %(levelname)s %(name)s: %(message)s`
- [x] `LOG_LEVEL=DEBUG` in `.env` produces debug output
- [x] Existing tests unaffected (no stdout pollution)

**Depends on:** none

---

### TASK-101: Shared resilient HTTP client factory

**Goal:** Single factory providing retry, backoff, realistic headers, and inter-request delays.

**Acceptance criteria:**
- [x] `create_client(*, headers, timeout, max_retries, backoff_base)` returns `httpx.AsyncClient`
- [x] Default User-Agent is a realistic Chrome string (rotated from a pool of 3-4)
- [x] Retries up to 3 times on status 429/500/502/503/504 with exponential backoff + jitter
- [x] Does NOT retry on 403 or 404 — logs warning instead
- [x] Retries on `httpx.ConnectTimeout` and `httpx.ReadTimeout`
- [x] `fetch_with_delay(client, url, *, min_delay, max_delay)` adds random sleep before request
- [x] No new external dependencies (pure asyncio retry loop)
- [x] Unit tests cover: success, retry-then-success, retry-exhausted, 403-no-retry

**Depends on:** none

---

### TASK-102: Migrate scrapers to shared HTTP client

**Goal:** All scrapers use `create_client()` as their default, gaining retry and realistic headers.

**Acceptance criteria:**
- [x] All 9 scrapers import `create_client` from `rentals_assistant.http`
- [x] Default path uses `create_client()`; DI path (`client` param) unchanged
- [x] RentalsCa uses `fetch_with_delay()` between city requests
- [x] Craigslist retains its specific UA string via `headers` override
- [x] All existing scraper unit tests pass without modification
- [x] New integration test: scraper receiving 503 retries and succeeds on 2nd attempt (mock transport)

**Depends on:** TASK-101

---

### TASK-103: Make notifier async

**Goal:** Eliminate event loop blocking by converting `send_alert()` to async.

**Acceptance criteria:**
- [x] `send_alert` is `async def` using `httpx.AsyncClient`
- [x] Pipeline calls `sent = await notifier(listing, result)`
- [x] `format_message()` remains sync (pure string formatting)
- [x] Existing notifier tests updated to `await` calls
- [x] Bot and scheduler still wire correctly (smoke test)

**Depends on:** TASK-101

---

### TASK-104: Concurrent scraper execution with semaphore

**Goal:** Run scrapers in parallel (bounded) instead of sequentially.

**Acceptance criteria:**
- [x] Pipeline uses `asyncio.gather` with per-scraper wrapper
- [x] New config field: `max_concurrent_scrapers: int = 4`
- [x] Semaphore limits concurrency to configured value
- [x] A failing scraper does not cancel others
- [x] Unit test verifies concurrent execution (mock timing or counters)
- [x] Unit test verifies semaphore=1 forces sequential behavior
- [x] Existing pipeline tests pass

**Depends on:** TASK-103

---

### TASK-105: Run summary with structured error reporting

**Goal:** After each run, report what worked/failed and listing counts via Telegram.

**Acceptance criteria:**
- [x] `RunResult` dataclass: `scrapers_ok`, `scrapers_failed`, `listings_found`, `listings_new`, `listings_notified`, `listings_rejected`
- [x] `pipeline.run()` returns `RunResult`
- [x] New `async send_summary(result: RunResult, settings) -> bool` in notifier
- [x] Summary sent only when at least one scraper failed (or `log_level == DEBUG`)
- [x] Format: scraper status + counts in a compact Telegram message
- [x] Scheduler and bot handle the new return value
- [x] Unit tests for `RunResult` population and `send_summary` formatting

**Depends on:** TASK-103, TASK-104
