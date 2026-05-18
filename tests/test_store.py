import sqlite3

import pytest

from rentals_assistant.store import Store

SAMPLE_LISTING = {
    "id": "abc123",
    "source": "kijiji",
    "external_id": "ext-001",
    "url": "https://kijiji.ca/v-1234",
    "title": "Cozy 2BR in Cambridge",
    "price_cad": 1800,
    "utilities": "included",
    "bedrooms": 2,
    "city": "Cambridge",
    "floor_level": "upper",
    "outdoor_space": 1,
    "parking_spots": 1,
    "pets": "cats_confirmed",
    "description": "Spacious apartment with balcony and modern kitchen",
    "bathrooms": 1.5,
    "score": 3,
    "tier": "strong",
    "notified": 0,
}


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_listings.db"


@pytest.fixture
def store(db_path):
    s = Store(db_path)
    yield s
    s.close()


# --- Schema ---

def test_creates_listings_table(db_path):
    Store(db_path).close()
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='listings'"
    ).fetchone()
    conn.close()
    assert row is not None


def test_schema_has_all_required_columns(db_path):
    Store(db_path).close()
    conn = sqlite3.connect(db_path)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(listings)")}
    conn.close()
    expected = {
        "id", "source", "external_id", "url", "title", "price_cad",
        "utilities", "bedrooms", "city", "floor_level", "outdoor_space",
        "parking_spots", "pets", "description", "bathrooms",
        "score", "tier", "first_seen", "last_seen", "notified",
    }
    assert expected <= cols


# --- is_new ---

def test_is_new_returns_true_for_unseen(store):
    assert store.is_new("nonexistent-id") is True


def test_is_new_returns_false_after_save(store):
    store.save(SAMPLE_LISTING)
    assert store.is_new(SAMPLE_LISTING["id"]) is False


# --- save / insert ---

def test_save_persists_all_fields(store, db_path):
    store.save(SAMPLE_LISTING)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM listings WHERE id = ?", (SAMPLE_LISTING["id"],)
    ).fetchone()
    conn.close()

    assert row["source"] == "kijiji"
    assert row["price_cad"] == 1800
    assert row["utilities"] == "included"
    assert row["bedrooms"] == 2
    assert row["city"] == "Cambridge"
    assert row["floor_level"] == "upper"
    assert row["outdoor_space"] == 1
    assert row["parking_spots"] == 1
    assert row["pets"] == "cats_confirmed"
    assert row["description"] == "Spacious apartment with balcony and modern kitchen"
    assert row["bathrooms"] == 1.5
    assert row["notified"] == 0


def test_score_and_tier_persisted(store, db_path):
    listing = {**SAMPLE_LISTING, "id": "score-test", "score": 4, "tier": "perfect"}
    store.save(listing)
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT score, tier FROM listings WHERE id = ?", ("score-test",)
    ).fetchone()
    conn.close()
    assert row[0] == 4
    assert row[1] == "perfect"


def test_save_sets_first_seen_and_last_seen(store, db_path):
    store.save(SAMPLE_LISTING)
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT first_seen, last_seen FROM listings WHERE id = ?",
        (SAMPLE_LISTING["id"],),
    ).fetchone()
    conn.close()
    assert row[0] is not None
    assert row[1] is not None


def test_save_preserves_first_seen_on_duplicate(store, db_path):
    store.save(SAMPLE_LISTING)
    conn = sqlite3.connect(db_path)
    first_seen_before = conn.execute(
        "SELECT first_seen FROM listings WHERE id = ?", (SAMPLE_LISTING["id"],)
    ).fetchone()[0]
    conn.close()

    store.save(SAMPLE_LISTING)
    conn = sqlite3.connect(db_path)
    first_seen_after = conn.execute(
        "SELECT first_seen FROM listings WHERE id = ?", (SAMPLE_LISTING["id"],)
    ).fetchone()[0]
    conn.close()

    assert first_seen_before == first_seen_after


# --- mark_notified ---

def test_mark_notified_sets_flag(store, db_path):
    store.save(SAMPLE_LISTING)
    store.mark_notified(SAMPLE_LISTING["id"])
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT notified FROM listings WHERE id = ?", (SAMPLE_LISTING["id"],)
    ).fetchone()
    conn.close()
    assert row[0] == 1


def test_mark_notified_is_idempotent(store, db_path):
    store.save(SAMPLE_LISTING)
    store.mark_notified(SAMPLE_LISTING["id"])
    store.mark_notified(SAMPLE_LISTING["id"])
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT notified FROM listings WHERE id = ?", (SAMPLE_LISTING["id"],)
    ).fetchone()
    conn.close()
    assert row[0] == 1


# --- Edge cases ---

def test_save_allows_null_optional_fields(store, db_path):
    minimal = {
        "id": "minimal-001",
        "source": "craigslist",
        "external_id": "cl-99",
        "url": "https://craigslist.org/abc",
        "title": "Room",
        "price_cad": 1500,
        "utilities": "unknown",
        "bedrooms": 2,
        "city": "Kitchener",
        "floor_level": "unknown",
        "outdoor_space": None,
        "parking_spots": None,
        "pets": "unknown",
        "score": None,
        "tier": None,
    }
    store.save(minimal)
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT outdoor_space, parking_spots, score, tier FROM listings WHERE id = ?",
        ("minimal-001",),
    ).fetchone()
    conn.close()
    assert row[0] is None
    assert row[1] is None
    assert row[2] is None
    assert row[3] is None


def test_multiple_listings_stored_independently(store):
    listing_a = {**SAMPLE_LISTING, "id": "aaa", "price_cad": 1600}
    listing_b = {**SAMPLE_LISTING, "id": "bbb", "price_cad": 1900}
    store.save(listing_a)
    store.save(listing_b)
    assert store.is_new("aaa") is False
    assert store.is_new("bbb") is False
    assert store.is_new("ccc") is True


def test_description_and_bathrooms_round_trip(store, db_path):
    listing = {
        "id": "roundtrip-001",
        "source": "kijiji",
        "external_id": "ext-999",
        "url": "https://example.com/123",
        "title": "Test Listing",
        "price_cad": 2000,
        "utilities": "unknown",
        "bedrooms": 2,
        "city": "Kitchener",
        "floor_level": "main",
        "outdoor_space": None,
        "parking_spots": None,
        "pets": "unknown",
        "description": "Beautiful apartment with great views",
        "bathrooms": 2.0,
        "score": 5,
        "tier": "strong",
        "notified": 0,
    }
    store.save(listing)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT description, bathrooms FROM listings WHERE id = ?", ("roundtrip-001",)
    ).fetchone()
    conn.close()
    assert row["description"] == "Beautiful apartment with great views"
    assert row["bathrooms"] == 2.0


def test_migration_adds_description_and_bathrooms(db_path):
    # Create a DB without the new columns (simulating old schema)
    old_create = """
    CREATE TABLE IF NOT EXISTS listings (
        id            TEXT PRIMARY KEY,
        source        TEXT,
        external_id   TEXT,
        url           TEXT,
        title         TEXT,
        price_cad     INTEGER,
        utilities     TEXT,
        bedrooms      INTEGER,
        city          TEXT,
        floor_level   TEXT,
        laundry_inunit INTEGER,
        outdoor_space INTEGER,
        parking_spots INTEGER,
        pets          TEXT,
        score         INTEGER,
        tier          TEXT,
        first_seen    DATETIME NOT NULL,
        last_seen     DATETIME NOT NULL,
        notified      INTEGER NOT NULL DEFAULT 0
    )
    """
    conn = sqlite3.connect(db_path)
    conn.execute(old_create)
    conn.close()

    # Now Store should migrate
    store = Store(db_path)

    # Verify columns exist
    conn = sqlite3.connect(db_path)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(listings)")}
    conn.close()
    assert "description" in cols
    assert "bathrooms" in cols

    store.close()


def test_description_and_bathrooms_none_values(store, db_path):
    listing = {
        "id": "none-test",
        "source": "kijiji",
        "external_id": "ext-none",
        "url": "https://example.com/none",
        "title": "Test None Values",
        "price_cad": 1500,
        "utilities": "unknown",
        "bedrooms": 2,
        "city": "Waterloo",
        "floor_level": "unknown",
        "outdoor_space": None,
        "parking_spots": None,
        "pets": "unknown",
        "description": None,
        "bathrooms": None,
        "score": None,
        "tier": None,
        "notified": 0,
    }
    store.save(listing)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT description, bathrooms FROM listings WHERE id = ?", ("none-test",)
    ).fetchone()
    conn.close()
    assert row["description"] is None
    assert row["bathrooms"] is None


def test_description_empty_string(store, db_path):
    listing = {
        "id": "empty-desc",
        "source": "kijiji",
        "external_id": "ext-empty",
        "url": "https://example.com/empty",
        "title": "Test Empty Description",
        "price_cad": 1600,
        "utilities": "unknown",
        "bedrooms": 2,
        "city": "Kitchener",
        "floor_level": "unknown",
        "outdoor_space": None,
        "parking_spots": None,
        "pets": "unknown",
        "description": "",
        "bathrooms": None,
        "score": None,
        "tier": None,
        "notified": 0,
    }
    store.save(listing)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT description FROM listings WHERE id = ?", ("empty-desc",)
    ).fetchone()
    conn.close()
    assert row["description"] == ""


def test_bathrooms_zero_and_fractional(store, db_path):
    listing_zero = {
        "id": "bath-zero",
        "source": "kijiji",
        "external_id": "ext-zero",
        "url": "https://example.com/zero",
        "title": "Test Zero Bathrooms",
        "price_cad": 1400,
        "utilities": "unknown",
        "bedrooms": 2,
        "city": "Cambridge",
        "floor_level": "unknown",
        "outdoor_space": None,
        "parking_spots": None,
        "pets": "unknown",
        "description": None,
        "bathrooms": 0.0,
        "score": None,
        "tier": None,
        "notified": 0,
    }
    store.save(listing_zero)

    listing_fractional = {
        "id": "bath-frac",
        "source": "kijiji",
        "external_id": "ext-frac",
        "url": "https://example.com/frac",
        "title": "Test Fractional Bathrooms",
        "price_cad": 1700,
        "utilities": "unknown",
        "bedrooms": 2,
        "city": "Cambridge",
        "floor_level": "unknown",
        "outdoor_space": None,
        "parking_spots": None,
        "pets": "unknown",
        "description": None,
        "bathrooms": 2.5,
        "score": None,
        "tier": None,
        "notified": 0,
    }
    store.save(listing_fractional)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row_zero = conn.execute(
        "SELECT bathrooms FROM listings WHERE id = ?", ("bath-zero",)
    ).fetchone()
    row_frac = conn.execute(
        "SELECT bathrooms FROM listings WHERE id = ?", ("bath-frac",)
    ).fetchone()
    conn.close()
    assert row_zero["bathrooms"] == 0.0
    assert row_frac["bathrooms"] == 2.5
