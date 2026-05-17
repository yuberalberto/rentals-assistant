import pytest

from rentals_assistant.scrapers.kijiji import (
    parse_floor_level,
    parse_laundry,
    parse_outdoor_space,
    parse_parking,
    parse_pets,
    parse_price,
    parse_utilities,
)

# ---------------------------------------------------------------------------
# parse_price
# ---------------------------------------------------------------------------

def test_parse_price_with_comma():
    assert parse_price("$1,850/month") == 1850


def test_parse_price_no_comma():
    assert parse_price("$1850/month") == 1850


def test_parse_price_per_month_phrase():
    assert parse_price("$1,750 per month") == 1750


def test_parse_price_none_when_no_number():
    assert parse_price("Please contact for price") is None


def test_parse_price_weekly_returns_none():
    # Weekly prices cannot be reliably converted; ignore them.
    assert parse_price("$500/week") is None


def test_parse_price_leading_text():
    assert parse_price("Rent: $1,900/mo") == 1900


# ---------------------------------------------------------------------------
# parse_pets
# ---------------------------------------------------------------------------

def test_parse_pets_cats_explicit_plural():
    assert parse_pets("2 cats welcome") == "cats_confirmed"


def test_parse_pets_cats_ok():
    assert parse_pets("Cats OK") == "cats_confirmed"


def test_parse_pets_cats_allowed():
    assert parse_pets("cats are allowed") == "cats_confirmed"


def test_parse_pets_generic_allowed():
    assert parse_pets("Pets allowed") == "allowed"


def test_parse_pets_no_pets():
    assert parse_pets("No pets") == "not_allowed"


def test_parse_pets_no_pets_please():
    assert parse_pets("No pets please.") == "not_allowed"


def test_parse_pets_pets_not_allowed():
    assert parse_pets("Pets not allowed") == "not_allowed"


def test_parse_pets_unknown_when_silent():
    assert parse_pets("Beautiful 2 bedroom apartment with modern kitchen.") is None


# ---------------------------------------------------------------------------
# parse_floor_level
# ---------------------------------------------------------------------------

def test_parse_floor_level_second_floor():
    assert parse_floor_level("2nd floor unit, great views") == "upper"


def test_parse_floor_level_third_floor():
    assert parse_floor_level("3rd floor apartment") == "upper"


def test_parse_floor_level_upper_keyword():
    assert parse_floor_level("Upper floor apartment") == "upper"


def test_parse_floor_level_main():
    assert parse_floor_level("Main floor unit") == "main"


def test_parse_floor_level_ground():
    assert parse_floor_level("Ground floor with yard access") == "main"


def test_parse_floor_level_basement():
    assert parse_floor_level("Basement apartment, cozy and affordable") == "basement"


def test_parse_floor_level_none_when_silent():
    assert parse_floor_level("Beautiful apartment in a great location.") is None


# ---------------------------------------------------------------------------
# parse_laundry
# ---------------------------------------------------------------------------

def test_parse_laundry_inunit_hyphenated():
    assert parse_laundry("In-unit laundry, washer/dryer") is True


def test_parse_laundry_washer_dryer_in_unit():
    assert parse_laundry("Washer and dryer in unit") is True


def test_parse_laundry_ensuite():
    assert parse_laundry("Ensuite laundry included") is True


def test_parse_laundry_shared():
    assert parse_laundry("Shared laundry on-site") is False


def test_parse_laundry_coin():
    assert parse_laundry("Coin laundry in building") is False


def test_parse_laundry_building():
    assert parse_laundry("Laundry in building") is False


def test_parse_laundry_unknown_when_silent():
    assert parse_laundry("Spacious 2BR with hardwood floors") is None


# ---------------------------------------------------------------------------
# parse_outdoor_space
# ---------------------------------------------------------------------------

def test_parse_outdoor_space_balcony():
    assert parse_outdoor_space("Private balcony with city views") is True


def test_parse_outdoor_space_yard():
    assert parse_outdoor_space("Large fenced backyard") is True


def test_parse_outdoor_space_patio():
    assert parse_outdoor_space("Patio access included") is True


def test_parse_outdoor_space_terrace():
    assert parse_outdoor_space("Rooftop terrace access") is True


def test_parse_outdoor_space_none_when_silent():
    assert parse_outdoor_space("Modern kitchen, hardwood floors, granite counters") is None


# ---------------------------------------------------------------------------
# parse_parking
# ---------------------------------------------------------------------------

def test_parse_parking_one_spot():
    assert parse_parking("1 parking spot included") == 1


def test_parse_parking_two_spots():
    assert parse_parking("2 parking spaces available") == 2


def test_parse_parking_double_garage():
    assert parse_parking("Double car garage") == 2


def test_parse_parking_included_no_number():
    assert parse_parking("Parking included") == 1


def test_parse_parking_none_when_silent():
    assert parse_parking("Spacious unit, great neighbourhood") is None


# ---------------------------------------------------------------------------
# parse_utilities
# ---------------------------------------------------------------------------

def test_parse_utilities_all_included():
    assert parse_utilities("All utilities included") == "included"


def test_parse_utilities_heat_hydro_water():
    assert parse_utilities("Heat, hydro, and water included") == "included"


def test_parse_utilities_utilities_included_phrase():
    assert parse_utilities("Rent is $1,800 utilities included") == "included"


def test_parse_utilities_extra():
    assert parse_utilities("Utilities extra") == "extra"


def test_parse_utilities_tenant_pays():
    assert parse_utilities("Tenant pays own utilities") == "extra"


def test_parse_utilities_plus_utilities():
    assert parse_utilities("$1,700/mo + utilities") == "extra"


def test_parse_utilities_unknown_when_silent():
    assert parse_utilities("Bright and spacious 2BR apartment") is None


# ---------------------------------------------------------------------------
# Integration test — hits live Kijiji site
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_kijiji_fetch_returns_results():
    from rentals_assistant.scrapers.kijiji import KijijiScraper

    scraper = KijijiScraper()
    listings = await scraper.fetch()

    assert len(listings) >= 1
    for listing in listings:
        assert listing.source == "kijiji"
        assert listing.url.startswith("https://www.kijiji.ca")
        assert listing.external_id
        assert listing.title
