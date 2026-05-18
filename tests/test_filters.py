import pytest

from rentals_assistant.config import Settings
from rentals_assistant.filters import passes_hard_filters
from rentals_assistant.models import RawListing


@pytest.fixture
def default_settings() -> Settings:
    """Default settings matching the spec defaults."""
    return Settings(
        telegram_token="test_token",
        telegram_chat_id="123",
        price_min=1400,
        price_max=2000,
        bedrooms=2,
        parking_min=1,
        laundry_required=True,
        min_notify_tier="perfect",
    )


def make_listing(**kwargs) -> RawListing:
    """A listing that passes all hard filters unless overridden."""
    defaults = {
        "source": "test",
        "external_id": "1",
        "url": "http://example.com",
        "title": "2BR Upper Unit",
        "price_cad": 1800,
        "bedrooms": 2,
        "floor_level": "upper",
        "laundry_inunit": True,
        "parking_spots": 1,
        "pets": "allowed",
    }
    defaults.update(kwargs)
    return RawListing(**defaults)


def make_settings(**kwargs) -> Settings:
    """Settings with defaults that pass all filters unless overridden."""
    defaults = {
        "telegram_token": "test_token",
        "telegram_chat_id": "123",
        "price_min": 1400,
        "price_max": 2000,
        "bedrooms": 2,
        "parking_min": 1,
        "laundry_required": True,
        "min_notify_tier": "perfect",
    }
    defaults.update(kwargs)
    return Settings(**defaults)


# --- price_cad ---

def test_rejects_price_above_ceiling(default_settings):
    assert not passes_hard_filters(make_listing(price_cad=2001), default_settings)

def test_rejects_price_well_above_ceiling(default_settings):
    assert not passes_hard_filters(make_listing(price_cad=3000), default_settings)

def test_passes_price_at_ceiling(default_settings):
    assert passes_hard_filters(make_listing(price_cad=2000), default_settings)

def test_passes_price_unknown(default_settings):
    assert passes_hard_filters(make_listing(price_cad=None), default_settings)

def test_respects_price_min_from_config():
    settings = make_settings(price_min=1500)
    assert not passes_hard_filters(make_listing(price_cad=1400), settings)
    assert passes_hard_filters(make_listing(price_cad=1500), settings)

def test_respects_price_max_from_config():
    settings = make_settings(price_max=1800)
    assert not passes_hard_filters(make_listing(price_cad=1801), settings)
    assert passes_hard_filters(make_listing(price_cad=1800), settings)


# --- bedrooms ---

def test_rejects_one_bedroom(default_settings):
    assert not passes_hard_filters(make_listing(bedrooms=1), default_settings)

def test_rejects_three_bedrooms(default_settings):
    assert not passes_hard_filters(make_listing(bedrooms=3), default_settings)

def test_passes_two_bedrooms(default_settings):
    assert passes_hard_filters(make_listing(bedrooms=2), default_settings)

def test_passes_bedrooms_unknown(default_settings):
    assert passes_hard_filters(make_listing(bedrooms=None), default_settings)

def test_respects_bedrooms_from_config():
    settings = make_settings(bedrooms=3)
    assert not passes_hard_filters(make_listing(bedrooms=2), settings)
    assert passes_hard_filters(make_listing(bedrooms=3), settings)


# --- floor_level ---

def test_rejects_basement(default_settings):
    assert not passes_hard_filters(make_listing(floor_level="basement"), default_settings)

def test_passes_floor_upper(default_settings):
    assert passes_hard_filters(make_listing(floor_level="upper"), default_settings)

def test_passes_floor_main(default_settings):
    assert passes_hard_filters(make_listing(floor_level="main"), default_settings)

def test_passes_floor_level_string_unknown(default_settings):
    assert passes_hard_filters(make_listing(floor_level="unknown"), default_settings)

def test_passes_floor_level_none(default_settings):
    assert passes_hard_filters(make_listing(floor_level=None), default_settings)


# --- pets removed from hard filter ---

def test_passes_pets_not_allowed(default_settings):
    """Pets removed from hard filter - all pet statuses pass."""
    assert passes_hard_filters(make_listing(pets="not_allowed"), default_settings)

def test_passes_pets_allowed(default_settings):
    assert passes_hard_filters(make_listing(pets="allowed"), default_settings)

def test_passes_pets_cats_confirmed(default_settings):
    assert passes_hard_filters(make_listing(pets="cats_confirmed"), default_settings)

def test_passes_pets_string_unknown(default_settings):
    assert passes_hard_filters(make_listing(pets="unknown"), default_settings)

def test_passes_pets_none(default_settings):
    assert passes_hard_filters(make_listing(pets=None), default_settings)


# --- laundry_inunit ---

def test_rejects_laundry_not_inunit(default_settings):
    assert not passes_hard_filters(make_listing(laundry_inunit=False), default_settings)

def test_passes_laundry_inunit(default_settings):
    assert passes_hard_filters(make_listing(laundry_inunit=True), default_settings)

def test_passes_laundry_unknown(default_settings):
    assert passes_hard_filters(make_listing(laundry_inunit=None), default_settings)

def test_passes_laundry_not_inunit_when_not_required():
    """When laundry_required=False, laundry not in unit passes."""
    settings = Settings(
        telegram_token="test_token",
        telegram_chat_id="123",
        price_min=1400,
        price_max=2000,
        bedrooms=2,
        parking_min=1,
        laundry_required=False,
        min_notify_tier="perfect",
    )
    assert passes_hard_filters(make_listing(laundry_inunit=False), settings)

def test_rejects_laundry_not_inunit_when_required():
    settings = make_settings(laundry_required=True)
    assert not passes_hard_filters(make_listing(laundry_inunit=False), settings)


# --- parking_spots ---

def test_rejects_zero_parking(default_settings):
    assert not passes_hard_filters(make_listing(parking_spots=0), default_settings)

def test_passes_one_parking(default_settings):
    assert passes_hard_filters(make_listing(parking_spots=1), default_settings)

def test_passes_two_parking(default_settings):
    assert passes_hard_filters(make_listing(parking_spots=2), default_settings)

def test_passes_parking_unknown(default_settings):
    assert passes_hard_filters(make_listing(parking_spots=None), default_settings)

def test_rejects_parking_below_min():
    """When parking_min=2, reject listings with 1 spot."""
    settings = Settings(
        telegram_token="test_token",
        telegram_chat_id="123",
        price_min=1400,
        price_max=2000,
        bedrooms=2,
        parking_min=2,
        laundry_required=True,
        min_notify_tier="perfect",
    )
    assert not passes_hard_filters(make_listing(parking_spots=1), settings)


# --- all fields unknown → pass (CHECK tier, not discard) ---

def test_passes_all_fields_unknown(default_settings):
    listing = RawListing(
        source="test",
        external_id="2",
        url="http://example.com/2",
        title="Unknown listing",
    )
    assert passes_hard_filters(listing, default_settings)


# --- full known listing that is a perfect pass ---

def test_passes_complete_valid_listing(default_settings):
    assert passes_hard_filters(make_listing(
        price_cad=1750,
        bedrooms=2,
        floor_level="upper",
        laundry_inunit=True,
        parking_spots=2,
        pets="cats_confirmed",
    ), default_settings)


# --- configurable behavior tests ---

def test_configurable_price_range():
    """Price range respects settings."""
    settings = Settings(
        telegram_token="test_token",
        telegram_chat_id="123",
        price_min=1200,
        price_max=1800,
        bedrooms=2,
        parking_min=1,
        laundry_required=True,
        min_notify_tier="perfect",
    )
    assert passes_hard_filters(make_listing(price_cad=1200), settings)
    assert passes_hard_filters(make_listing(price_cad=1800), settings)
    assert not passes_hard_filters(make_listing(price_cad=1199), settings)
    assert not passes_hard_filters(make_listing(price_cad=1801), settings)

def test_configurable_bedrooms():
    """Bedrooms filter respects settings."""
    settings = Settings(
        telegram_token="test_token",
        telegram_chat_id="123",
        price_min=1400,
        price_max=2000,
        bedrooms=3,
        parking_min=1,
        laundry_required=True,
        min_notify_tier="perfect",
    )
    assert passes_hard_filters(make_listing(bedrooms=3), settings)
    assert not passes_hard_filters(make_listing(bedrooms=2), settings)
    assert not passes_hard_filters(make_listing(bedrooms=4), settings)
