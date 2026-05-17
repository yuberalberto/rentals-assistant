
from rentals_assistant.filters import passes_hard_filters
from rentals_assistant.models import RawListing


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


# --- price_cad ---

def test_rejects_price_above_ceiling():
    assert not passes_hard_filters(make_listing(price_cad=2001))

def test_rejects_price_well_above_ceiling():
    assert not passes_hard_filters(make_listing(price_cad=3000))

def test_passes_price_at_ceiling():
    assert passes_hard_filters(make_listing(price_cad=2000))

def test_passes_price_unknown():
    assert passes_hard_filters(make_listing(price_cad=None))


# --- bedrooms ---

def test_rejects_one_bedroom():
    assert not passes_hard_filters(make_listing(bedrooms=1))

def test_rejects_three_bedrooms():
    assert not passes_hard_filters(make_listing(bedrooms=3))

def test_passes_two_bedrooms():
    assert passes_hard_filters(make_listing(bedrooms=2))

def test_passes_bedrooms_unknown():
    assert passes_hard_filters(make_listing(bedrooms=None))


# --- floor_level ---

def test_rejects_basement():
    assert not passes_hard_filters(make_listing(floor_level="basement"))

def test_passes_floor_upper():
    assert passes_hard_filters(make_listing(floor_level="upper"))

def test_passes_floor_main():
    assert passes_hard_filters(make_listing(floor_level="main"))

def test_passes_floor_level_string_unknown():
    assert passes_hard_filters(make_listing(floor_level="unknown"))

def test_passes_floor_level_none():
    assert passes_hard_filters(make_listing(floor_level=None))


# --- pets ---

def test_rejects_pets_not_allowed():
    assert not passes_hard_filters(make_listing(pets="not_allowed"))

def test_passes_pets_allowed():
    assert passes_hard_filters(make_listing(pets="allowed"))

def test_passes_pets_cats_confirmed():
    assert passes_hard_filters(make_listing(pets="cats_confirmed"))

def test_passes_pets_string_unknown():
    assert passes_hard_filters(make_listing(pets="unknown"))

def test_passes_pets_none():
    assert passes_hard_filters(make_listing(pets=None))


# --- laundry_inunit ---

def test_rejects_laundry_not_inunit():
    assert not passes_hard_filters(make_listing(laundry_inunit=False))

def test_passes_laundry_inunit():
    assert passes_hard_filters(make_listing(laundry_inunit=True))

def test_passes_laundry_unknown():
    assert passes_hard_filters(make_listing(laundry_inunit=None))


# --- parking_spots ---

def test_rejects_zero_parking():
    assert not passes_hard_filters(make_listing(parking_spots=0))

def test_passes_one_parking():
    assert passes_hard_filters(make_listing(parking_spots=1))

def test_passes_two_parking():
    assert passes_hard_filters(make_listing(parking_spots=2))

def test_passes_parking_unknown():
    assert passes_hard_filters(make_listing(parking_spots=None))


# --- all fields unknown → pass (CHECK tier, not discard) ---

def test_passes_all_fields_unknown():
    listing = RawListing(
        source="test",
        external_id="2",
        url="http://example.com/2",
        title="Unknown listing",
    )
    assert passes_hard_filters(listing)


# --- full known listing that is a perfect pass ---

def test_passes_complete_valid_listing():
    assert passes_hard_filters(make_listing(
        price_cad=1750,
        bedrooms=2,
        floor_level="upper",
        laundry_inunit=True,
        parking_spots=2,
        pets="cats_confirmed",
    ))
