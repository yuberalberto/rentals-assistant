from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from rentals_assistant.models import RawListing
from rentals_assistant.scrapers.craigslist import (
    CraigslistScraper,
    _parse_city,
    _parse_craigslist_price,
    _text,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


# ── _parse_craigslist_price ───────────────────────────────────────────────────

def test_parse_craigslist_price_extracts_number():
    assert _parse_craigslist_price("$1,850 / 2br - Bright Upper Floor") == 1850


def test_parse_craigslist_price_returns_none_when_missing():
    assert _parse_craigslist_price("Price TBD - Coming Soon") is None


def test_parse_craigslist_price_returns_none_for_empty():
    assert _parse_craigslist_price("") is None


# ── _parse_city ───────────────────────────────────────────────────────────────

def test_parse_city_extracts_from_parentheses():
    assert _parse_city("$1,850 / 2br - Bright (Kitchener)") == "kitchener"


def test_parse_city_returns_none_when_no_parentheses():
    assert _parse_city("$1,850 / 2br - Bright Upper Floor") is None


def test_parse_city_lowercases_result():
    assert _parse_city("Some Title (Waterloo)") == "waterloo"


# ── _text helper ──────────────────────────────────────────────────────────────

def test_text_returns_stripped_text():
    from xml.etree.ElementTree import Element, SubElement
    parent = Element("item")
    child = SubElement(parent, "{http://purl.org/rss/1.0/}title")
    child.text = "  Hello World  "
    assert _text(parent, "{http://purl.org/rss/1.0/}title") == "Hello World"


def test_text_returns_none_when_tag_missing():
    from xml.etree.ElementTree import Element
    parent = Element("item")
    assert _text(parent, "{http://purl.org/rss/1.0/}missing") is None


# ── return type ───────────────────────────────────────────────────────────────

def test_parse_returns_list():
    xml = load_fixture("craigslist_hamilton.xml")
    scraper = CraigslistScraper(client=MagicMock())
    assert isinstance(scraper._parse(xml), list)


def test_parse_returns_raw_listing_instances():
    xml = load_fixture("craigslist_hamilton.xml")
    scraper = CraigslistScraper(client=MagicMock())
    assert all(isinstance(r, RawListing) for r in scraper._parse(xml))


def test_parse_returns_four_listings():
    xml = load_fixture("craigslist_hamilton.xml")
    scraper = CraigslistScraper(client=MagicMock())
    assert len(scraper._parse(xml)) == 4


# ── required identity fields ──────────────────────────────────────────────────

def test_parse_source_is_craigslist():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[0].source == "craigslist"


def test_parse_extracts_title():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert "$1,850 / 2br - Bright Upper Floor 2BR" in result[0].title


def test_parse_extracts_url():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[0].url == "https://hamilton.craigslist.org/apa/1.html"


def test_parse_extracts_external_id():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[0].external_id == "1"


# ── price ─────────────────────────────────────────────────────────────────────

def test_parse_extracts_price_cad():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[0].price_cad == 1850


def test_parse_price_second_item():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[1].price_cad == 1650


def test_parse_handles_missing_price_gracefully():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[3].price_cad is None


# ── city ──────────────────────────────────────────────────────────────────────

def test_parse_extracts_city():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[0].city == "kitchener"


def test_parse_city_second_item():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[1].city == "cambridge"


# ── pets ──────────────────────────────────────────────────────────────────────

def test_parse_pets_cats_confirmed():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[0].pets == "cats_confirmed"


def test_parse_pets_allowed():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[1].pets == "allowed"


def test_parse_pets_not_allowed():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[2].pets == "not_allowed"


# ── floor level ───────────────────────────────────────────────────────────────

def test_parse_floor_level_upper():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[0].floor_level == "upper"


def test_parse_floor_level_main():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[1].floor_level == "main"


def test_parse_floor_level_basement():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[2].floor_level == "basement"


# ── laundry ─────────────────────────────────────────────────────────────────────

def test_parse_laundry_inunit():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[0].laundry_inunit is True


def test_parse_laundry_shared():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[1].laundry_inunit is False


# ── outdoor space ───────────────────────────────────────────────────────────────

def test_parse_outdoor_balcony():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[0].outdoor_space is True


def test_parse_outdoor_unknown():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[1].outdoor_space is None


# ── parking ───────────────────────────────────────────────────────────────────

def test_parse_parking_two_spots():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[0].parking_spots == 2


def test_parse_parking_one_spot():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[1].parking_spots == 1


# ── utilities ─────────────────────────────────────────────────────────────────

def test_parse_utilities_included():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[0].utilities == "included"


def test_parse_utilities_extra():
    xml = load_fixture("craigslist_hamilton.xml")
    result = CraigslistScraper(client=MagicMock())._parse(xml)
    assert result[1].utilities == "extra"


# ── edge cases ─────────────────────────────────────────────────────────────────

def test_parse_handles_malformed_xml_gracefully():
    bad_xml = "<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>" \
              "<item><title>Bad</title><description>No link</description></item>" \
              "</rdf:RDF>"
    result = CraigslistScraper(client=MagicMock())._parse(bad_xml)
    assert isinstance(result, list)
    assert len(result) == 0


def test_parse_empty_xml_returns_empty_list():
    result = CraigslistScraper(client=MagicMock())._parse(
        '<?xml version="1.0"?><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<channel rdf:about="x"><items><rdf:Seq></rdf:Seq></items></channel></rdf:RDF>'
    )
    assert result == []


def test_parse_handles_invalid_xml_gracefully():
    result = CraigslistScraper(client=MagicMock())._parse("not xml at all")
    assert isinstance(result, list)
    assert result == []


# ── fetch() ───────────────────────────────────────────────────────────────────

async def test_fetch_hits_rss_url():
    mock_response = MagicMock()
    mock_response.text = load_fixture("craigslist_hamilton.xml")
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    await CraigslistScraper(client=mock_client).fetch()

    called_url = mock_client.get.call_args.args[0]
    assert "hamilton.craigslist.org" in called_url
    assert "format=rss" in called_url


async def test_fetch_returns_raw_listing_instances():
    mock_response = MagicMock()
    mock_response.text = load_fixture("craigslist_hamilton.xml")
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    results = await CraigslistScraper(client=mock_client).fetch()
    assert all(isinstance(r, RawListing) for r in results)
    assert len(results) == 4
