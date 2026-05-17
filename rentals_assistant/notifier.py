import httpx

from rentals_assistant.config import Settings, load_config
from rentals_assistant.models import RawListing
from rentals_assistant.scorer import ScoringResult

_TIER_EMOJI = {
    "perfect": "🟢",
    "strong": "🟡",
    "check": "🔵",
}

_TIER_LABEL = {
    "perfect": "Perfect match",
    "strong": "Strong match",
    "check": "Check it",
}

_PETS_LINE = {
    "cats_confirmed": "Cats: confirmed 🐱",
    "allowed": "Pets: allowed",
    "not_allowed": "Pets: not allowed ⚠️",
}


def format_message(listing: RawListing, result: ScoringResult) -> str:
    tier_emoji = _TIER_EMOJI.get(result.tier, "🔵")
    tier_label = _TIER_LABEL.get(result.tier, "Check it")
    source = listing.source.replace("_", " ").title()

    header = f"{tier_emoji} {tier_label} — {source}"

    price_str = f"${listing.price_cad:,}/mo" if listing.price_cad is not None else "price ?"
    utils_flag = " ★ utilities incl." if "★" in result.flags else ""
    price_line = f"2BR · {price_str}{utils_flag}"

    location_flags = [f for f in result.flags if f != "★"]
    city_str = listing.city or "Unknown city"
    location_parts = [city_str, *location_flags]
    location_line = " · ".join(location_parts)

    lines = [header, price_line, location_line]

    pets_line = _PETS_LINE.get(listing.pets or "")
    if pets_line:
        lines.append(pets_line)

    lines.append(listing.url)

    return "\n".join(lines)


def send_alert(
    listing: RawListing,
    result: ScoringResult,
    settings: Settings | None = None,
) -> bool:
    if settings is None:
        settings = load_config()

    text = format_message(listing, result)
    url = f"https://api.telegram.org/bot{settings.telegram_token}/sendMessage"

    try:
        resp = httpx.post(url, json={"chat_id": settings.telegram_chat_id, "text": text})
        resp.raise_for_status()
        return True
    except Exception:
        return False
