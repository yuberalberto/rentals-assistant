# Fly.io Deployment

## 1. Problem
The rentals-assistant scheduler must run 24/7 without requiring the user's PC to stay on.

## 2. What
Deploy the rentals-assistant pipeline to Fly.io so APScheduler fires 3×/day (08:00, 13:00, 18:00 EST) from a persistent cloud container. Playwright/Chromium runs natively inside the container. SQLite persists on a Fly Volume. GitHub Actions auto-deploys on every push to `main`.

## 3. How

**Runtime image:** `mcr.microsoft.com/playwright/python:v1.44.0-jammy`
- Includes Chromium + all system deps for Playwright out of the box

**Entry point:** `python -m rentals_assistant` (APScheduler process — TASK-010)

**Fly.io config (`fly.toml`):**
- App name: `rentals-assistant`
- Region: `yyz` (Toronto)
- VM: `shared-cpu-1x`, 256 MB RAM (upgradeable if Playwright needs more)
- Volume: 1 GB mounted at `/data` — SQLite path set to `/data/listings.db`
- No HTTP service exposed (worker process only)

**Secrets (via `fly secrets set`):**
- `TELEGRAM_TOKEN`
- `TELEGRAM_CHAT_ID`

**Env vars (in `fly.toml` — non-sensitive):**
- `TZ=America/Toronto`
- `PRICE_MIN=1400`
- `PRICE_MAX=2000`
- `LOG_LEVEL=INFO`
- `DB_PATH=/data/listings.db`

**CI/CD (`fly-deploy.yml`):**
- Trigger: push to `main`
- Steps: checkout → `flyctl deploy --remote-only`
- Auth: `FLY_API_TOKEN` stored as GitHub Actions secret

**Health check:**
- Daily Telegram ping at 00:00 EST — scheduler sends a "✅ rentals-assistant alive" message
- Implemented as an additional APScheduler job in the scheduler module

**Files involved:**
| File | Change |
|---|---|
| `Dockerfile` | New — Playwright base image, copy app, install deps via uv |
| `fly.toml` | New — Fly app config |
| `.github/workflows/fly-deploy.yml` | New — GitHub Actions deploy pipeline |
| `rentals_assistant/config.py` | Add `db_path: str = "listings.db"` field |
| `rentals_assistant/scheduler.py` | Add daily heartbeat job (TASK-010 dependency) |

---

## 4. Tasks

### TASK-D01: Dockerfile
**Goal:** Build a working Docker image with Python 3.14 + Playwright/Chromium + app dependencies
**Acceptance criteria:**
- [ ] `docker build .` succeeds locally
- [ ] `docker run` starts the app without errors
- [ ] Playwright can launch Chromium inside the container (`playwright install --with-deps chromium`)
- [ ] App dependencies installed via `uv sync` inside image
**Depends on:** none

### TASK-D02: fly.toml + Fly Volume
**Goal:** Configure Fly.io app with yyz region, worker process, and 1 GB persistent volume
**Acceptance criteria:**
- [ ] `fly.toml` defines app, region `yyz`, no HTTP service, volume mount at `/data`
- [ ] `fly volumes create` creates 1 GB volume named `listings_data`
- [ ] `DB_PATH=/data/listings.db` env var present and picked up by `config.py`
- [ ] `fly deploy` succeeds and container starts
**Depends on:** TASK-D01

### TASK-D03: Secrets + env vars
**Goal:** Load all runtime config from Fly secrets and fly.toml env — no `.env` file in container
**Acceptance criteria:**
- [ ] `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` set via `fly secrets set`
- [ ] `config.py` reads `db_path` from env with default `"listings.db"`
- [ ] App starts without `.env` file present
- [ ] Secrets are NOT committed to the repo
**Depends on:** TASK-D02

### TASK-D04: GitHub Actions deploy pipeline
**Goal:** Auto-deploy to Fly.io on every push to `main`
**Acceptance criteria:**
- [ ] `.github/workflows/fly-deploy.yml` triggers on `push: branches: [main]`
- [ ] `FLY_API_TOKEN` stored as GitHub Actions repository secret
- [ ] Push to `main` triggers successful deploy in Actions tab
- [ ] Failed deploy does NOT take down the running container (Fly rollback)
**Depends on:** TASK-D03

### TASK-D05: Daily heartbeat
**Goal:** Scheduler sends a Telegram ping daily at 00:00 EST to confirm the process is alive
**Acceptance criteria:**
- [ ] New APScheduler job fires daily at midnight Toronto time
- [ ] Sends "✅ rentals-assistant alive [date]" to Telegram
- [ ] Job failure does NOT crash the scheduler
- [ ] Unit test verifies heartbeat job is registered
**Depends on:** TASK-010 (scheduler implementation)
