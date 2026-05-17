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
        "parking_spots", "pets", "score", "tier", "first_seen", "last_seen",
        "notified",
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
