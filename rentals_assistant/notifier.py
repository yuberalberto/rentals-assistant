import httpx

from rentals_assistant.config import Settings, load_config
from rentals_assistant.models import RawListing
from rentals_assistant.pipeline import RunResult
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
    
    # Add bathrooms if available, format whole numbers without decimal
    if listing.bathrooms is not None:
        bathrooms_val = listing.bathrooms if listing.bathrooms % 1 != 0 else int(listing.bathrooms)
        bathrooms_str = f" · {bathrooms_val}BA"
    else:
        bathrooms_str = ""
    price_line = f"2BR{bathrooms_str} · {price_str}{utils_flag}"

    location_flags = [f for f in result.flags if f != "★"]
    city_str = listing.city or "Unknown city"
    location_parts = [city_str, *location_flags]
    location_line = " · ".join(location_parts)

    lines = [header, price_line, location_line]

    # Add truncated description if available
    if listing.description:
        truncated = listing.description[:100] if len(listing.description) > 100 else listing.description
        lines.append(truncated)

    pets_line = _PETS_LINE.get(listing.pets or "")
    if pets_line:
        lines.append(pets_line)

    lines.append(listing.url)

    return "\n".join(lines)


async def _send_telegram(text: str, settings: Settings) -> bool:
    url = f"https://api.telegram.org/bot{settings.telegram_token}/sendMessage"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url, json={"chat_id": settings.telegram_chat_id, "text": text}
            )
            resp.raise_for_status()
        return True
    except Exception:
        return False


async def send_alert(
    listing: RawListing,
    result: ScoringResult,
    settings: Settings | None = None,
) -> bool:
    if settings is None:
        settings = load_config()

    text = format_message(listing, result)
    return await _send_telegram(text, settings)


async def send_summary(
    result: RunResult,
    settings: Settings | None = None,
) -> bool:
    if settings is None:
        settings = load_config()

    if result.scrapers_failed == 0 and settings.log_level != "DEBUG":
        return False

    lines = [
        "📊 Run Summary",
        "",
        f"Scrapers: {result.scrapers_ok} OK, {result.scrapers_failed} failed",
        f"Listings: {result.listings_found} found, {result.listings_new} new, {result.listings_notified} notified, {result.listings_rejected} rejected",
    ]
    text = "\n".join(lines)

    return await _send_telegram(text, settings)
