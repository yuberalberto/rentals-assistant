from dataclasses import dataclass
from typing import Optional


@dataclass
class RawListing:
    source: str
    external_id: str
    url: str
    title: str
    price_cad: Optional[int] = None
    bedrooms: Optional[int] = None
    city: Optional[str] = None
    floor_level: Optional[str] = None       # "upper" | "main" | "basement" | "unknown"
    laundry_inunit: Optional[bool] = None   # True | False | None (unknown)
    outdoor_space: Optional[bool] = None    # True | False | None (unknown)
    parking_spots: Optional[int] = None     # 0, 1, 2, … | None (unknown)
    pets: Optional[str] = None              # "cats_confirmed" | "allowed" | "not_allowed" | "unknown"
    utilities: Optional[str] = None         # "included" | "extra" | "unknown"
