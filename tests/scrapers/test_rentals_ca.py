from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from rentals_assistant.models import RawListing
from rentals_assistant.scrapers.rentals_ca import RentalsCaScraper

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


# ── return type ───────────────────────────────────────────────────────────────

def test_parse_returns_list():
    html = load_fixture("rentals_ca_kitchener.html")
    scraper = RentalsCaScraper(client=MagicMock())
    assert isinstance(scraper._parse(html, "kitchener"), list)


def test_parse_returns_raw_listing_instances():
    html = load_fixture("rentals_ca_kitchener.html")
    scraper = RentalsCaScraper(client=MagicMock())
    assert all(isinstance(r, RawListing) for r in scraper._parse(html, "kitchener"))


def test_parse_returns_three_listings():
    html = load_fixture("rentals_ca_kitchener.html")
    scraper = RentalsCaScraper(client=MagicMock())
    assert len(scraper._parse(html, "kitchener")) == 3


# ── required identity fields ──────────────────────────────────────────────────

def test_parse_source_is_rentals_ca():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[0].source == "rentals_ca"


def test_parse_extracts_title():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[0].title == "Bright 2BR Upper Unit - All Utilities Included"


def test_parse_extracts_url():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[0].url == "https://rentals.ca/rental/111111-bright-2br-kitchener"


def test_parse_extracts_external_id():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[0].external_id == "111111"


def test_parse_city_from_parameter():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[0].city == "kitchener"


# ── price ─────────────────────────────────────────────────────────────────────

def test_parse_extracts_price_cad():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[0].price_cad == 1850


def test_parse_price_with_plus_utilities_suffix():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[2].price_cad == 1950


# ── bedrooms ──────────────────────────────────────────────────────────────────

def test_parse_extracts_bedrooms():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[0].bedrooms == 2


# ── utilities ─────────────────────────────────────────────────────────────────

def test_parse_utilities_included():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[0].utilities == "included"


def test_parse_utilities_extra():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[2].utilities == "extra"


def test_parse_utilities_unknown():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[1].utilities is None


# ── floor level ───────────────────────────────────────────────────────────────

def test_parse_floor_level_upper():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[0].floor_level == "upper"


def test_parse_floor_level_main():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[2].floor_level == "main"


def test_parse_floor_level_unknown():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[1].floor_level is None


# ── pets ──────────────────────────────────────────────────────────────────────

def test_parse_pets_cats_confirmed():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[0].pets == "cats_confirmed"


def test_parse_pets_not_allowed():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[1].pets == "not_allowed"


def test_parse_pets_allowed():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[2].pets == "allowed"


# ── laundry ───────────────────────────────────────────────────────────────────

def test_parse_laundry_inunit_from_insuite():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[0].laundry_inunit is True


def test_parse_laundry_inunit_from_inunit():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[2].laundry_inunit is True


def test_parse_laundry_unknown():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[1].laundry_inunit is None


# ── outdoor space ─────────────────────────────────────────────────────────────

def test_parse_outdoor_space_balcony():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[0].outdoor_space is True


def test_parse_outdoor_space_yard():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[2].outdoor_space is True


def test_parse_outdoor_space_unknown():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[1].outdoor_space is None


# ── parking ───────────────────────────────────────────────────────────────────

def test_parse_parking_two_spots():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[0].parking_spots == 2


def test_parse_parking_one_spot():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[2].parking_spots == 1


def test_parse_parking_unknown():
    html = load_fixture("rentals_ca_kitchener.html")
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result[1].parking_spots is None


# ── fetch() — covers all three cities ────────────────────────────────────────

async def test_fetch_queries_kitchener_waterloo_cambridge():
    mock_response = MagicMock()
    mock_response.text = load_fixture("rentals_ca_kitchener.html")
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    await RentalsCaScraper(client=mock_client).fetch()

    called_urls = [call.args[0] for call in mock_client.get.call_args_list]
    assert any("kitchener" in u for u in called_urls)
    assert any("waterloo" in u for u in called_urls)
    assert any("cambridge" in u for u in called_urls)


async def test_fetch_aggregates_results_from_all_cities():
    mock_response = MagicMock()
    mock_response.text = load_fixture("rentals_ca_kitchener.html")
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    result = await RentalsCaScraper(client=mock_client).fetch()

    assert len(result) == 9  # 3 listings × 3 cities


# ── edge cases ────────────────────────────────────────────────────────────────

def test_parse_skips_card_without_title_link():
    html = """<html><body>
      <article class="listing-card" data-listing-id="999">
        <div class="listing-card__details">
          <h2>No link here</h2>
          <p class="listing-card__price">$1,500/month</p>
          <p class="listing-card__beds">2 Bed</p>
          <p class="listing-card__description">Some unit.</p>
        </div>
      </article>
    </body></html>"""
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert result == []


def test_parse_price_missing_returns_none():
    html = """<html><body>
      <article class="listing-card" data-listing-id="888">
        <div class="listing-card__details">
          <h2><a class="listing-card__title" href="/rental/888-no-price">No Price Unit</a></h2>
          <p class="listing-card__beds">2 Bed</p>
          <p class="listing-card__description">A unit without price listed.</p>
        </div>
      </article>
    </body></html>"""
    result = RentalsCaScraper(client=MagicMock())._parse(html, "kitchener")
    assert len(result) == 1
    assert result[0].price_cad is None


def test_parse_empty_html_returns_empty_list():
    result = RentalsCaScraper(client=MagicMock())._parse("<html><body></body></html>", "kitchener")
    assert result == []
