import sqlite3
from datetime import UTC, datetime
from pathlib import Path

_CREATE_TABLE = """
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

_INSERT = """
INSERT INTO listings (
    id, source, external_id, url, title, price_cad, utilities,
    bedrooms, city, floor_level, laundry_inunit, outdoor_space, parking_spots,
    pets, score, tier, first_seen, last_seen, notified
) VALUES (
    :id, :source, :external_id, :url, :title, :price_cad, :utilities,
    :bedrooms, :city, :floor_level, :laundry_inunit, :outdoor_space, :parking_spots,
    :pets, :score, :tier, :first_seen, :last_seen, :notified
)
ON CONFLICT(id) DO UPDATE SET last_seen = excluded.last_seen
"""


class Store:
    def __init__(self, db_path: str | Path = "listings.db") -> None:
        self._conn = sqlite3.connect(Path(db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    def is_new(self, listing_id: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM listings WHERE id = ?", (listing_id,)
        )
        return cur.fetchone() is None

    def save(self, listing: dict) -> None:
        now = datetime.now(UTC).isoformat()
        row = {
            "id": listing["id"],
            "source": listing.get("source"),
            "external_id": listing.get("external_id"),
            "url": listing.get("url"),
            "title": listing.get("title"),
            "price_cad": listing.get("price_cad"),
            "utilities": listing.get("utilities"),
            "bedrooms": listing.get("bedrooms"),
            "city": listing.get("city"),
            "floor_level": listing.get("floor_level"),
            "laundry_inunit": listing.get("laundry_inunit"),
            "outdoor_space": listing.get("outdoor_space"),
            "parking_spots": listing.get("parking_spots"),
            "pets": listing.get("pets"),
            "score": listing.get("score"),
            "tier": listing.get("tier"),
            "first_seen": listing.get("first_seen", now),
            "last_seen": now,
            "notified": listing.get("notified", 0),
        }
        self._conn.execute(_INSERT, row)
        self._conn.commit()

    def mark_notified(self, listing_id: str) -> None:
        self._conn.execute(
            "UPDATE listings SET notified = 1 WHERE id = ?", (listing_id,)
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
