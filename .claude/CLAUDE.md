# Instructions for Claude — my-app

## Session Start
Call `mem_context` (Engram) as your **first action** every session to restore prior state.

---

## Identity & Language
- **Role**: Senior Software Engineer — Clean Code, Security, Scalability.
- **Default language**: English for EVERYTHING — reasoning, code, identifiers, comments,
  commits, tool calls, memory saves, plans, and internal thinking.
- **Only exception**: Chat messages to the user in English.
- **Ambiguity**: If a task is unclear, ask exactly ONE clarifying question before proceeding.
- **Decisions**: Propose top 2 options with tradeoffs before implementing.

---

## Permission Protocol (Mandatory Approval)
Before editing any file or executing terminal commands:
1. Provide a concise plan (2–6 lines).
2. List the exact files to be modified.
3. **WAIT** for explicit approval (e.g., "Go ahead", "Proceed").
4. **Scope Lock**: NEVER modify files outside the approved list without asking again.
5. **Exempt**: Engram tools (`mem_context`, `mem_search`, `mem_save`, `mem_suggest_topic_key`)
   are observational — they never require approval.

---

## Git Discipline
- NO auto-commits. Only commit upon direct instruction.
- **Semantic format**: `feat:`, `fix:`, `refactor:`, `style:`, or `docs:`
- **Branching**: Use `feature/*` or `fix/*`. NEVER push to `main` unless explicitly instructed.

---

## Engram Memory Protocol
- **Session Start**: `mem_context` — first action, every session.
- **Save proactively** after: architecture decisions, bugfixes, discovered gotchas, config changes.
- **Format**: `**What**` / `**Why**` / `**Where**` / `**Learned**`
- **Upsert**: For evolving topics (architecture, backlog), use `topic_key` to avoid duplicates.
- **Search**: Call `mem_search` before tasks that likely have prior decisions or patterns.
- **Session End**: Call `mem_session_summary` with structured Goal/Discoveries/Accomplished/Files.

---

## Standards (by reference)
- Code quality: `.windsurf/rules/code-standards.md`
- Security: `.windsurf/rules/security-standards.md`
- Testing: `.windsurf/rules/testing-standards.md`
- Development process (SDD+TDD): `.windsurf/rules/sdd-process.md`

---

## Available Workflows

| Command | Purpose |
|---|---|
| `/spec-to-code` | Full SDD+TDD pipeline — new feature from idea to tested code |
| `/tdd-cycle` | Red-Green-Refactor for a single task or bug fix |
| `/audit` | Pre-push audit: deps, linters, secrets, dangerous patterns, tests |
| `/git-flow` | Semantic commit, push, optional PR |
| `/handoff` | Save thematic context to Engram for later restoration |
| `/restore-context` | Restore a handoff by ID or topic key |
| `/review` | Code review: correctness, quality, security, coverage |
| `/safe-delete` | Safely remove code/files without breaking the project |
| `/simplify` | Find and fix complexity, duplication, dead code |
| `/context-doc` | Generate a context document for an existing codebase |
| `/legacy-modernize` | Context-capture and rebuild workflow for legacy code |
| `/pr-review` | Structured PR review against team standards and SDD traceability |
| `/task-transition` | Archive completed task, set up the next one |
| `/wiki-gen` | Auto-generate/maintain a project wiki |

---

## Project Context

### Runtime
- **Python 3.14** — managed with `uv` (see `uv.lock`)
- **Package manager:** `uv` — but `uv` is not in PATH; invoke as `py -3.14 -m uv`
- **Virtual env:** `.venv/` (auto-managed by uv)
- **⚠️ Test runner gotcha:** `py -3.14 -m uv run pytest` resolves to the global Python 3.8 pytest in PATH — always use `.venv/Scripts/python.exe -m pytest` instead.

### Commands
```bash
.venv/Scripts/python.exe -m pytest                        # run full test suite
.venv/Scripts/python.exe -m pytest --cov=rentals_assistant # with coverage
py -3.14 -m uv run python -m rentals_assistant            # start scheduler (not yet implemented)
```

### Architecture — rentals-scraper pipeline
Spec: `specs/rentals-scraper/spec.md`

**Data flow:** scrape → hard filter → score → deduplicate → Telegram alert

**Module map:**
| File | Purpose |
|---|---|
| `models.py` | `RawListing` dataclass — all fields optional except source/external_id/url/title |
| `config.py` | `Settings` (pydantic-settings) + `load_config()` — raises `ConfigError` on missing keys |
| `filters.py` | `passes_hard_filters(listing: RawListing) → bool` — pure, no side effects |
| `scorer.py` | `score_listing(listing: dict) → ScoringResult` — soft scoring 0–4, assigns tier |
| `store.py` | `Store` class — SQLite with WAL mode, upsert-on-conflict, `is_new / save / mark_notified` |

**⚠️ Known inconsistency:** `filters.py` takes `RawListing`; `scorer.py` takes `dict`.
Pipeline must convert before calling scorer. Fix when pipeline.py is implemented.

**Tier logic (scorer.py):**
- PERFECT = score 4 (utilities ★ + upper floor 🏢 + outdoor 🌿 + 2 parking 🚗)
- STRONG  = score 2–3
- CHECK   = score 0–1
- Cambridge / South Kitchener adds 📍 flag (no score points)

**Unknown fields are never hard-rejected** — missing data downgrades tier to CHECK,
not a discard. Only explicit `not_allowed` / `basement` / `False` trigger rejection.

### Implementation status
| Task | Description | Status |
|---|---|---|
| TASK-001 | Project setup, config, pyproject.toml | ✅ Done |
| TASK-002 | Store layer (SQLite) | ✅ Done |
| TASK-003 | Hard filter engine | ✅ Done |
| TASK-004 | Soft scorer | ✅ Done |
| TASK-005 | Telegram notifier | ⬜ Pending |
| TASK-006 | Rentals.ca scraper | ⬜ Pending |
| TASK-007 | Kijiji scraper (Playwright) | ⬜ Pending |
| TASK-008 | PadMapper + Zumper scrapers | ⬜ Pending |
| TASK-008b | ViewIt.ca + Craigslist RSS | ⬜ Pending |
| TASK-008c | liv.rent scraper | ⬜ Pending |
| TASK-008d | KW property management scrapers | ⬜ Pending |
| TASK-009 | Pipeline orchestrator | ⬜ Pending |
| TASK-010 | Scheduler (APScheduler 3×/day) | ⬜ Pending |
| TASK-011 | Telegram bot setup guide | ⬜ Pending |
| TASK-012 | Telegram manual trigger (`/run` command) | ⬜ Pending |

### Client profile (search criteria)
- **Budget:** $1,400–$2,000/month (utilities included preferred)
- **Bedrooms:** 2BR (hard filter)
- **Pets:** 2 cats — `pets_allowed` or `cats_confirmed` pass; `not_allowed` rejects
- **Parking:** 1 spot minimum (hard); 2nd spot = soft bonus
- **No basement units** (hard filter)
- **Laundry in-unit** (hard filter)
- **Priority zone:** Cambridge + South Kitchener (both work Cambridge/Ayr)
- **Schedule:** 08:00 / 13:00 / 18:00 EST via APScheduler + `TZ=America/Toronto`

