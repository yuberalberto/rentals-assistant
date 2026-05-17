from dataclasses import dataclass


@dataclass
class RawListing:
    source: str
    external_id: str
    url: str
    title: str
    price_cad: int | None = None
    bedrooms: int | None = None
    city: str | None = None
    floor_level: str | None = None       # "upper" | "main" | "basement" | "unknown"
    laundry_inunit: bool | None = None   # True | False | None (unknown)
    outdoor_space: bool | None = None    # True | False | None (unknown)
    parking_spots: int | None = None     # 0, 1, 2, … | None (unknown)
    pets: str | None = None              # "cats_confirmed" | "allowed" | "not_allowed" | "unknown"
    utilities: str | None = None         # "included" | "extra" | "unknown"
