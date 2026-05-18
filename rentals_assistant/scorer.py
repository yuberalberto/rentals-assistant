from dataclasses import dataclass, field
from typing import List

PROXIMITY_CITIES = {"cambridge", "south kitchener"}

TIER_PERFECT = "perfect"
TIER_STRONG = "strong"
TIER_CHECK = "check"


@dataclass
class ScoringResult:
    score: int
    tier: str
    flags: List[str] = field(default_factory=list)


def _assign_tier(score: int) -> str:
    if score == 7:
        return TIER_PERFECT
    if score >= 5:
        return TIER_STRONG
    return TIER_CHECK


def score_listing(listing: dict) -> ScoringResult:
    points = 0
    flags: List[str] = []

    if listing.get("utilities") == "included":
        points += 1
        flags.append("★")

    if listing.get("floor_level") in ("upper", "main"):
        points += 1
        flags.append("🏢")

    if listing.get("outdoor_space"):
        points += 1
        flags.append("🌿")

    if (listing.get("parking_spots") or 0) >= 2:
        points += 1
        flags.append("🚗")

    if listing.get("pets") in ("allowed", "cats_confirmed"):
        points += 1
        flags.append("🐱")

    if (listing.get("bathrooms") or 0) >= 1.5:
        points += 1
        flags.append("🚿")

    city = (listing.get("city") or "").lower()
    if any(label in city for label in PROXIMITY_CITIES):
        points += 1
        flags.append("📍")

    return ScoringResult(score=points, tier=_assign_tier(points), flags=flags)
