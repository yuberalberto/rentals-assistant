# Improve Results Curation (~130 → ~20 alerts)

## Dependency Graph & Execution Order

```
TASK-CUR-001 (Kijiji fix)        ─────────────────────────────────────┐
TASK-CUR-002 (model+store)       ──┬──> TASK-CUR-005 (enrichment) ───┤
TASK-CUR-003 (parsers)           ──┘                                  ├──> TASK-CUR-007 (pipeline)
TASK-CUR-004 (config)            ─────────────────────────────────────┤
TASK-CUR-006 (scoring)           ← TASK-CUR-002                      ┘
TASK-CUR-008 (notifier)          ← TASK-CUR-002
```

| Group | Tasks | Status |
|-------|-------|--------|
| **1 — parallel** | 001, 002, 003, 004 | ✅ |
| **2 — parallel** | 005, 006, 008 | ✅ |
| **3 — final**    | 007 | ✅ |

---

## 1. Problem

First real pipeline run produced ~130 Telegram notifications — far too many for practical use. Raw scraper output goes straight to filters without enrichment, missing-data listings pass through, all tiers (including CHECK) are notified, and basement detection misses common euphemisms.

## 2. What

A multi-pronged curation overhaul that:
- Fixes Kijiji duplicate parsers by consolidating to shared `parsers.py`
- Adds an enrichment stage that fills missing fields from title+description before filtering
- Expands scoring from 0-4 to 0-7 with new criteria (pets, bathrooms, proximity)
- Introduces a configurable tier gate (`MIN_NOTIFY_TIER`) so only high-quality matches trigger notifications
- Moves hardcoded filter criteria to `Settings` for `.env` configurability
- Improves basement detection with additional euphemism patterns
- Enriches Telegram messages with bathrooms and description snippet

**Design decisions:**
- `description` and `bathrooms` fields added to `RawListing` + DB
- Pets removed from hard filter (user lives with 2 cats in a "no pets" apartment) — moved to scoring
- Utilities stays as scoring only, not a hard filter
- Laundry stays as hard filter (`laundry_inunit == False` → reject)
- Tiers: PERFECT=7, STRONG>=5, CHECK<5
- kw_property/liv_rent inline parsers left as-is — enrichment compensates

## 3. How

**New pipeline flow:** `scrape → enrich → validate → hard_filters → score → tier_gate → dedupe → notify`

**Modules affected:**
| Module | Change |
|--------|--------|
| `scrapers/kijiji.py` | Remove 7 inline parsers, import from `parsers.py` |
| `scrapers/parsers.py` | Add `parse_bathrooms()`, enhance basement detection |
| `models.py` | Add `description: Optional[str]`, `bathrooms: Optional[float]` |
| `store.py` | Add columns + `_migrate()` for existing DBs |
| `config.py` | Add `BEDROOMS`, `PARKING_MIN`, `LAUNDRY_REQUIRED`, `MIN_NOTIFY_TIER` |
| `filters.py` | Accept `Settings` param, remove pets/utilities, use config values |
| `enrichment.py` | NEW — `enrich()` + `validate()` |
| `scorer.py` | Expand to 0-7, add pets/bathrooms/proximity criteria |
| `pipeline.py` | Wire enrichment, validation, tier gate |
| `notifier.py` | Add bathrooms + description to Telegram message |

**No new dependencies.** All changes use existing libraries.

## 4. Tasks

### TASK-CUR-001: Kijiji — Remove Duplicate Parsers
**Goal:** Fix Kijiji data quality by using shared `parsers.py`.

**Files:**
- `rentals_assistant/scrapers/kijiji.py` — delete 7 inline parser functions + regex constants (lines 34-129), import from `parsers.py`
- `tests/test_kijiji_scraper.py` — update imports to `rentals_assistant.scrapers.parsers`

**Acceptance criteria:**
- [x] `kijiji.py` has zero `def parse_*` functions
- [x] Imports all 7 parsers from `rentals_assistant.scrapers.parsers`
- [x] `parse_price("$1,850")` → `1850` (bare-dollar fallback now works)
- [x] All existing kijiji parser tests pass
- [x] New test for bare-dollar price pattern

**Depends on:** none

---

### TASK-CUR-002: Model + Store — Add `description` and `bathrooms`
**Goal:** Extend data model for enrichment and display.

**Files:**
- `rentals_assistant/models.py` — add `description: Optional[str] = None`, `bathrooms: Optional[float] = None`
- `rentals_assistant/store.py` — add `description TEXT`, `bathrooms REAL` to `_CREATE_TABLE` + `_INSERT`, add `_migrate()` for existing DBs
- `rentals_assistant/pipeline.py` — add both to `_listing_to_record()`
- `tests/test_store.py` — update schema test + `SAMPLE_LISTING`

**Scraper updates** (pass `description` through):
- `rentals_assistant/scrapers/kijiji.py` — pass `body` as `description`
- Other scrapers that already extract description text — pass it through

**Acceptance criteria:**
- [x] `RawListing` has `description: Optional[str]` and `bathrooms: Optional[float]`
- [x] DB schema includes both columns
- [x] Listing with `bathrooms=1.5` and `description="text"` round-trips through save/read
- [x] `_migrate()` adds columns to existing DBs via `ALTER TABLE`
- [x] All existing tests pass

**Depends on:** none

---

### TASK-CUR-003: Parsers — Better Basement Detection + `parse_bathrooms`
**Goal:** Catch disguised basements and extract bathroom count as float.

**Files:**
- `rentals_assistant/scrapers/parsers.py` — enhance `parse_floor_level`, add `parse_bathrooms()`
- `tests/test_parsers.py` (NEW)

**New basement patterns:** `"lower level"`, `"lower unit"`, `"garden level"`, `"walkout basement"`, `"bsmt"`, `"bsmnt"`

**`parse_bathrooms` returns `float | None`:**
- `"1.5 bath"` → `1.5`
- `"2 bath"` → `2.0`
- `"one and a half bath"` → `1.5`
- `"half bath"` or `"powder room"` + `"full bath"` → `1.5`
- No mention → `None`

**Acceptance criteria:**
- [x] All 6 new basement patterns → `"basement"`
- [x] Existing floor_level patterns unchanged
- [x] `parse_bathrooms` handles decimal, integer, and word variants
- [x] `tests/test_parsers.py` with full coverage

**Depends on:** none

---

### TASK-CUR-004: Config — Configurable Search Profile
**Goal:** Move hardcoded filter criteria to `Settings` so user can adjust via `.env`.

**Files:**
- `rentals_assistant/config.py` — add/connect settings
- `rentals_assistant/filters.py` — accept `Settings` param, use config values
- `tests/test_filters.py` — update to pass settings, test configurable behavior
- `tests/test_config.py` — test new defaults

**New/connected settings:**
```env
PRICE_MIN=1400          # already exists, connect to filters
PRICE_MAX=2000          # already exists, connect to filters
BEDROOMS=2              # new, was hardcoded
PARKING_MIN=1           # new, was hardcoded
LAUNDRY_REQUIRED=true   # new, was hardcoded
MIN_NOTIFY_TIER=perfect # new, for pipeline tier gate
```

**Removed from hard filter:** pets (moved to scoring), utilities (scoring only)

**`passes_hard_filters(listing, settings)` new signature:**
- Price: `settings.price_min <= price_cad <= settings.price_max` (if known)
- Bedrooms: `== settings.bedrooms` (if known)
- Floor: reject `"basement"` (always, not configurable)
- Laundry: reject `False` if `settings.laundry_required` (if known)
- Parking: reject `< settings.parking_min` (if known)
- ~~Pets~~: removed
- ~~Utilities~~: removed

**Acceptance criteria:**
- [x] All filter criteria read from `Settings`
- [x] `price_min`/`price_max` actually connected (were dead config)
- [x] Pets and utilities removed from hard filter
- [x] `MIN_NOTIFY_TIER` available in settings with default `"perfect"`
- [x] Existing tests updated and passing

**Depends on:** none

---

### TASK-CUR-005: Enrichment Module — `enrich()` + `validate()`
**Goal:** Post-processing stage that fills missing fields from title+description.

**Files:**
- `rentals_assistant/enrichment.py` (NEW)
- `tests/test_enrichment.py` (NEW)

**`enrich(listing: RawListing) -> RawListing`:**
- Concatenates `listing.title + " " + (listing.description or "")`
- Re-parses using all shared parsers from `rentals_assistant.scrapers.parsers`
- Only fills fields that are `None` (never overwrites)
- Uses `dataclasses.replace()` for immutability
- Parsers reused: `parse_price`, `parse_bedrooms`, `parse_bathrooms`, `parse_floor_level`, `parse_laundry`, `parse_outdoor_space`, `parse_parking`, `parse_pets`, `parse_utilities`

**`validate(listing: RawListing) -> bool`:**
- Returns `False` if `price_cad is None`
- Returns `True` otherwise

**Acceptance criteria:**
- [x] Fills None fields from title+description
- [x] Never overwrites non-None fields
- [x] `validate()` rejects `price_cad=None`, accepts any number
- [x] Pure functions, no side effects

**Depends on:** TASK-CUR-002 (bathrooms field), TASK-CUR-003 (parse_bathrooms)

---

### TASK-CUR-006: Scoring — Expand to 0-7 with New Criteria
**Goal:** Richer scoring with pets, bathrooms, and proximity as point criteria.

**Files:**
- `rentals_assistant/scorer.py` — add 3 criteria, update tiers
- `tests/test_scorer.py` — update all tier/score tests

**Scoring (0-7):**
| Criterion | Points | Flag | Condition |
|-----------|--------|------|-----------|
| Utilities included | +1 | ★ | `utilities == "included"` |
| Upper/main floor | +1 | 🏢 | `floor_level in ("upper", "main")` |
| Outdoor space | +1 | 🌿 | `outdoor_space == True` |
| 2+ parking | +1 | 🚗 | `parking_spots >= 2` |
| Pets friendly | +1 | 🐱 | `pets in ("allowed", "cats_confirmed")` |
| Bathrooms >= 1.5 | +1 | 🚿 | `bathrooms >= 1.5` |
| Proximity zone | +1 | 📍 | city contains "cambridge" or "south kitchener" |

**Tiers:**
- PERFECT = 7
- STRONG >= 5
- CHECK < 5

**Acceptance criteria:**
- [x] All 7 criteria score correctly
- [x] Tier boundaries: 7=PERFECT, 5-6=STRONG, 0-4=CHECK
- [x] Pets, bathrooms, proximity award points (not just flags)
- [x] Floor awards point for both "upper" and "main"
- [x] All scorer tests pass

**Depends on:** TASK-CUR-002 (bathrooms field)

---

### TASK-CUR-007: Pipeline — Wire Enrichment + Tier Gate
**Goal:** Integrate enrichment and configurable tier gate into pipeline.

**Files:**
- `rentals_assistant/pipeline.py`
- `tests/test_pipeline.py`

**New flow:** `scrape → enrich → validate → hard_filters → score → tier_gate → dedupe → notify`

```python
from rentals_assistant.enrichment import enrich, validate

for listing in all_listings:
    listing = enrich(listing)
    listing_id = make_listing_id(...)
    record = _listing_to_record(listing_id, listing)

    if not validate(listing):                          # price mandatory
        store.save({**record, "score": None, "tier": None, "notified": 0})
        listings_rejected += 1
        continue

    if not passes_hard_filters(listing, settings):     # configurable filters
        store.save({**record, "score": None, "tier": None, "notified": 0})
        listings_rejected += 1
        continue

    result = score_listing(listing.__dict__)
    store.save({**record, "score": result.score, "tier": result.tier, "notified": 0})

    tier_order = {"check": 0, "strong": 1, "perfect": 2}
    min_tier = settings.min_notify_tier
    if tier_order.get(result.tier, 0) < tier_order.get(min_tier, 0):
        continue                                       # tier gate

    if is_new:
        ...                                            # dedupe + notify
```

**Acceptance criteria:**
- [x] Enrichment runs before filtering
- [x] Validation rejects no-price listings
- [x] Tier gate respects `settings.min_notify_tier`
- [x] CHECK listings saved but not notified (with default config)
- [x] All existing + new pipeline tests pass

**Depends on:** TASK-CUR-004 (config), TASK-CUR-005 (enrichment), TASK-CUR-006 (scoring)

---

### TASK-CUR-008: Notifier — Add Bathrooms + Description
**Goal:** Richer Telegram messages with bathrooms and short description.

**Files:**
- `rentals_assistant/notifier.py` — update `format_message()`
- `tests/test_notifier.py` — update format tests

**Message format update:**
```
🟢 Perfect match — Kijiji
2BR · 1.5BA · $1,850/mo ★
Cambridge 🏢🌿🚗🐱📍
In-unit laundry, balcony, 2 parking spots...
https://www.kijiji.ca/...
```

- Add `1.5BA` next to bedrooms
- Add truncated description (first ~100 chars) as a summary line
- Keep existing flag system

**Acceptance criteria:**
- [x] Bathrooms shown in message (e.g., `1.5BA`)
- [x] Description truncated and shown
- [x] Handles `None` bathrooms/description gracefully
- [x] All notifier tests pass

**Depends on:** TASK-CUR-002 (model fields)

---

## 5. Verification

1. `.venv/Scripts/python.exe -m pytest` — full suite passes
2. `.venv/Scripts/python.exe -m pytest --cov=rentals_assistant` — coverage maintained
3. Manual: run bot `/run` → expect ~15-25 notifications with `MIN_NOTIFY_TIER=strong`, ~5-10 with `perfect`
4. Verify CHECK tier listings saved in DB but not notified
5. Change `.env` tier setting → verify different notification volume
