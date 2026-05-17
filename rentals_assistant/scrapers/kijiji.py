import logging
import re

from playwright.async_api import Page, async_playwright

from rentals_assistant.http import create_client  # noqa: F401
from rentals_assistant.models import RawListing
from rentals_assistant.scrapers.base import Scraper

logger = logging.getLogger(__name__)

# Kitchener-Waterloo and Cambridge location codes on Kijiji.
# URL pattern: /b-apartments-condos/{region}/{page-N/}{loc_code}
_CITIES = [
    (
        "https://www.kijiji.ca/b-apartments-condos/kitchener-waterloo",
        "c37l1700212",
        "Kitchener",
    ),
    (
        "https://www.kijiji.ca/b-apartments-condos/cambridge",
        "c37l1700209",
        "Cambridge",
    ),
]
_PAGES_PER_CITY = 2
_QS = "?ad=offering&numBedrooms=2"


# ---------------------------------------------------------------------------
# Pure parsing helpers — unit-testable, no Playwright dependency
# ---------------------------------------------------------------------------

def parse_price(text: str) -> int | None:
    lower = text.lower()
    if re.search(r'\$[\d,]+\s*/\s*week', lower):
        return None
    m = re.search(r'\$\s*([\d,]+)\s*(?:/\s*mo(?:nth)?|per\s+month)', lower)
    if m:
        return int(m.group(1).replace(',', ''))
    return None


_CATS_CONFIRMED = re.compile(
    r"cats?\s+(?:ok|allowed|welcome|permitted|friendly|are\s+(?:ok|allowed|welcome))"
    r"|\d+\s+cats?\s+(?:ok|welcome|allowed|fine)",
    re.IGNORECASE,
)
_PETS_ALLOWED = re.compile(r"pets?\s+(?:allowed|welcome|ok|permitted|friendly)", re.IGNORECASE)
_PETS_DENIED = re.compile(r"no\s+pets?|pets?\s+not\s+allowed|no\s+animals?", re.IGNORECASE)


def parse_pets(body: str) -> str | None:
    if _CATS_CONFIRMED.search(body):
        return "cats_confirmed"
    if _PETS_DENIED.search(body):
        return "not_allowed"
    if _PETS_ALLOWED.search(body):
        return "allowed"
    return None


def parse_floor_level(body: str) -> str | None:
    lower = body.lower()
    if "basement" in lower:
        return "basement"
    if re.search(r"\b(?:upper\s+floor|[2-9]\w*\s+floor|second\s+floor|third\s+floor)", lower):
        return "upper"
    if re.search(r"\b(?:main\s+floor|ground\s+floor|1st\s+floor|first\s+floor)", lower):
        return "main"
    return None


_LAUNDRY_INUNIT = re.compile(
    r"in[- ]?unit\s+laundry|laundry\s+in[- ]?unit"
    r"|ensuite\s+laundry|in[- ]?suite\s+laundry"
    r"|washer\s+(?:and\s+)?dryer\s+in\s+(?:the\s+)?unit",
    re.IGNORECASE,
)
_LAUNDRY_SHARED = re.compile(
    r"shared\s+laundry|coin\s+laundry|common\s+laundry"
    r"|laundry\s+in\s+(?:the\s+)?build|laundry\s+on[- ]?site|laundry\s+room",
    re.IGNORECASE,
)


def parse_laundry(body: str) -> bool | None:
    if not re.search(r"laundry|washer|dryer", body, re.IGNORECASE):
        return None
    if _LAUNDRY_INUNIT.search(body):
        return True
    if _LAUNDRY_SHARED.search(body):
        return False
    return None


_OUTDOOR = re.compile(
    r"balcony|backyard|back\s+yard|patio|terrace|\byards?\b|\bdeck\b", re.IGNORECASE
)


def parse_outdoor_space(body: str) -> bool | None:
    return True if _OUTDOOR.search(body) else None


def parse_parking(body: str) -> int | None:
    lower = body.lower()
    if re.search(r"double\s+(?:car\s+)?garage|double\s+parking", lower):
        return 2
    m = re.search(r"(\d+)\s+parking", lower)
    if m:
        return int(m.group(1))
    if re.search(r"\bparking\b", lower):
        return 1
    return None


def parse_utilities(body: str) -> str | None:
    lower = body.lower()
    if re.search(r"\b(?:utilities|heat|hydro|water)\b", lower) and "included" in lower:
        return "included"
    if re.search(r"all\s+utilities", lower):
        return "included"
    if re.search(
        r"utilities\s+extra|utilities\s+not\s+incl|tenant\s+pays|\+\s*utilities|\bplus\s+utilities\b",
        lower,
    ):
        return "extra"
    return None


# ---------------------------------------------------------------------------
# Playwright scraping helpers
# ---------------------------------------------------------------------------

def _page_url(base: str, loc: str, page_num: int) -> str:
    if page_num == 1:
        return f"{base}/{loc}{_QS}"
    return f"{base}/page-{page_num}/{loc}{_QS}"


async def _extract_card(card, city: str) -> RawListing | None:
    link_el = await card.query_selector("a[data-testid='listing-link']")
    if not link_el:
        link_el = await card.query_selector("a[href*='/v-']")
    if not link_el:
        return None

    href = await link_el.get_attribute("href") or ""
    url = href if href.startswith("http") else f"https://www.kijiji.ca{href}"

    # Extract listing ID from the last path segment (e.g. /.../1731317387)
    listing_id = url.rstrip("/").split("/")[-1]
    if not listing_id or not listing_id.isdigit():
        return None

    title_el = (
        await card.query_selector("[data-testid='listing-title']")
        or await card.query_selector("a[class*='title']")
        or await card.query_selector("h3")
    )
    title = (await title_el.inner_text()).strip() if title_el else ""
    if not title:
        return None

    price_el = (
        await card.query_selector("[data-testid='listing-price']")
        or await card.query_selector("[class*='price']")
    )
    price_text = (await price_el.inner_text()).strip() if price_el else ""

    desc_el = (
        await card.query_selector("[data-testid='listing-description']")
        or await card.query_selector("[class*='description']")
    )
    body = (await desc_el.inner_text()).strip() if desc_el else ""

    full_text = f"{title} {body}"

    return RawListing(
        source="kijiji",
        external_id=listing_id,
        url=url,
        title=title,
        price_cad=parse_price(price_text),
        bedrooms=2,
        city=city,
        floor_level=parse_floor_level(full_text),
        laundry_inunit=parse_laundry(full_text),
        outdoor_space=parse_outdoor_space(full_text),
        parking_spots=parse_parking(full_text),
        pets=parse_pets(full_text),
        utilities=parse_utilities(full_text),
    )


async def _scrape_page(page: Page, url: str, city: str) -> list[RawListing]:
    results: list[RawListing] = []
    try:
        await page.goto(url, wait_until="networkidle", timeout=60_000)
        await page.wait_for_selector("[data-testid='listing-card']", timeout=30_000)
    except Exception as exc:
        logger.warning("Failed to load %s: %s", url, exc)
        return results

    cards = await page.query_selector_all("[data-testid='listing-card']")
    for card in cards:
        try:
            listing = await _extract_card(card, city)
            if listing:
                results.append(listing)
        except Exception as exc:
            logger.debug("Skipping card: %s", exc)

    logger.info("Kijiji %s — %s: %d listings", city, url, len(results))
    return results


# ---------------------------------------------------------------------------
# Public scraper class
# ---------------------------------------------------------------------------

class KijijiScraper(Scraper):
    async def fetch(self) -> list[RawListing]:
        listings: list[RawListing] = []
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers({
                "Accept-Language": "en-CA,en;q=0.9",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            })
            for base_url, loc_code, city in _CITIES:
                for page_num in range(1, _PAGES_PER_CITY + 1):
                    url = _page_url(base_url, loc_code, page_num)
                    page_results = await _scrape_page(page, url, city)
                    listings.extend(page_results)
            await browser.close()
        return listings
