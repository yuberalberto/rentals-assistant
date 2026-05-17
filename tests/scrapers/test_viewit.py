from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from rentals_assistant.models import RawListing
from rentals_assistant.scrapers.viewit import ViewItScraper, _parse_viewit_price

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


# ── _parse_viewit_price ───────────────────────────────────────────────────────

def test_parse_viewit_price_extracts_number():
    assert _parse_viewit_price("$1,850") == 1850


def test_parse_viewit_price_returns_none_when_missing():
    assert _parse_viewit_price("") is None


def test_parse_viewit_price_handles_no_dollar_sign():
    assert _parse_viewit_price("1850") is None


# ── return type ───────────────────────────────────────────────────────────────

def test_parse_returns_list():
    html = load_fixture("viewit_listings.html")
    scraper = ViewItScraper(client=MagicMock())
    assert isinstance(scraper._parse(html, "Kitchener"), list)


def test_parse_returns_raw_listing_instances():
    html = load_fixture("viewit_listings.html")
    scraper = ViewItScraper(client=MagicMock())
    assert all(isinstance(r, RawListing) for r in scraper._parse(html, "Kitchener"))


def test_parse_returns_three_listings():
    html = load_fixture("viewit_listings.html")
    scraper = ViewItScraper(client=MagicMock())
    assert len(scraper._parse(html, "Kitchener")) == 3


# ── required identity fields ────────────────────────────────────────────────

def test_parse_source_is_viewit():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[0].source == "viewit"


def test_parse_extracts_title():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[0].title == "Bright 2BR Upper Unit near Downtown"


def test_parse_extracts_url():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert "href.aspx" in result[0].url
    assert "cid=5001" in result[0].url


def test_parse_extracts_external_id():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[0].external_id == "5001"


def test_parse_city_from_parameter():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "cambridge")
    assert result[0].city == "cambridge"


# ── price ─────────────────────────────────────────────────────────────────────

def test_parse_extracts_price_cad():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[0].price_cad == 1850


def test_parse_price_with_utilities_suffix():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[1].price_cad == 1950


def test_parse_price_missing_returns_none():
    html = """<!DOCTYPE html><body>
      <section class="featuredListing">
        <a href="//www.viewit.ca/href.aspx?cid=9999">
          <article data-id="9999">
            <div class="featuredListing-name">No Price Listed</div>
            <div class="featuredListing-details"></div>
          </article>
        </a>
      </section>
    </body></html>"""
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert len(result) == 1
    assert result[0].price_cad is None


# ── bedrooms ──────────────────────────────────────────────────────────────────

def test_parse_bedrooms_hardcoded_to_two():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[0].bedrooms == 2


# ── utilities ─────────────────────────────────────────────────────────────────

def test_parse_utilities_included():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[0].utilities == "included"


def test_parse_utilities_extra():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[1].utilities == "extra"


def test_parse_utilities_unknown():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[2].utilities is None


# ── floor level ───────────────────────────────────────────────────────────────

def test_parse_floor_level_upper():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[0].floor_level == "upper"


def test_parse_floor_level_main():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[1].floor_level == "main"


def test_parse_floor_level_basement():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[2].floor_level == "basement"


# ── pets ──────────────────────────────────────────────────────────────────────

def test_parse_pets_cats_confirmed():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[0].pets == "cats_confirmed"


def test_parse_pets_not_allowed():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[2].pets == "not_allowed"


def test_parse_pets_allowed():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[1].pets == "allowed"


# ── laundry ───────────────────────────────────────────────────────────────────

def test_parse_laundry_inunit():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[0].laundry_inunit is True


def test_parse_laundry_shared():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[1].laundry_inunit is False


def test_parse_laundry_unknown():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[2].laundry_inunit is False  # "coin laundry" maps to False


# ── outdoor space ─────────────────────────────────────────────────────────────

def test_parse_outdoor_space_balcony():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[0].outdoor_space is True


def test_parse_outdoor_space_unknown():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[1].outdoor_space is None


# ── parking ───────────────────────────────────────────────────────────────────

def test_parse_parking_two_spots():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[0].parking_spots == 2


def test_parse_parking_one_spot():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[1].parking_spots == 1


def test_parse_parking_unknown():
    html = load_fixture("viewit_listings.html")
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result[2].parking_spots is None


# ── edge cases ────────────────────────────────────────────────────────────────

def test_parse_skips_card_without_link():
    html = """<!DOCTYPE html><body>
      <section class="featuredListing">
        <article data-id="9999">
          <div class="featuredListing-name">No Link</div>
        </article>
      </section>
    </body></html>"""
    result = ViewItScraper(client=MagicMock())._parse(html, "Kitchener")
    assert result == []


def test_parse_empty_html_returns_empty_list():
    result = ViewItScraper(client=MagicMock())._parse("<html><body></body></html>", "Kitchener")
    assert result == []


# ── fetch() — covers all three cities ─────────────────────────────────────────

async def test_fetch_queries_kitchener_waterloo_cambridge():
    mock_response = MagicMock()
    mock_response.text = load_fixture("viewit_listings.html")
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    await ViewItScraper(client=mock_client).fetch()

    called_urls = [call.args[0] for call in mock_client.get.call_args_list]
    assert any("Kitchener" in u for u in called_urls)
    assert any("Waterloo" in u for u in called_urls)
    assert any("Cambridge" in u for u in called_urls)


async def test_fetch_aggregates_results_from_all_cities():
    mock_response = MagicMock()
    mock_response.text = load_fixture("viewit_listings.html")
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    result = await ViewItScraper(client=mock_client).fetch()
    assert len(result) == 9  # 3 listings x 3 cities
