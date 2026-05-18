import pytest
from rentals_assistant.models import RawListing
from rentals_assistant.enrichment import enrich, validate


class TestEnrich:
    """Tests for enrich() function."""

    def test_enrich_fills_missing_price_from_title(self):
        """Should fill missing price_cad from title."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="$1,850/mo 2BR apartment",
            price_cad=None,
        )
        result = enrich(listing)
        assert result.price_cad == 1850

    def test_enrich_fills_missing_bedrooms_from_title(self):
        """Should fill missing bedrooms from title."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="2 bed apartment",
            price_cad=1850,
            bedrooms=None,
        )
        result = enrich(listing)
        assert result.bedrooms == 2

    def test_enrich_fills_missing_bathrooms_from_title(self):
        """Should fill missing bathrooms from title."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="2BR 1.5 bath apartment",
            price_cad=1850,
            bedrooms=2,
            bathrooms=None,
        )
        result = enrich(listing)
        assert result.bathrooms == 1.5

    def test_enrich_fills_missing_floor_level_from_description(self):
        """Should fill missing floor_level from description."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="2BR apartment",
            price_cad=1850,
            bedrooms=2,
            description="Upper floor unit with balcony",
            floor_level=None,
        )
        result = enrich(listing)
        assert result.floor_level == "upper"

    def test_enrich_fills_missing_laundry_from_description(self):
        """Should fill missing laundry_inunit from description."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="2BR apartment",
            price_cad=1850,
            bedrooms=2,
            description="In-unit laundry",
            laundry_inunit=None,
        )
        result = enrich(listing)
        assert result.laundry_inunit is True

    def test_enrich_fills_missing_outdoor_space_from_description(self):
        """Should fill missing outdoor_space from description."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="2BR apartment",
            price_cad=1850,
            bedrooms=2,
            description="Nice balcony",
            outdoor_space=None,
        )
        result = enrich(listing)
        assert result.outdoor_space is True

    def test_enrich_fills_missing_parking_from_description(self):
        """Should fill missing parking_spots from description."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="2BR apartment",
            price_cad=1850,
            bedrooms=2,
            description="2 parking spots",
            parking_spots=None,
        )
        result = enrich(listing)
        assert result.parking_spots == 2

    def test_enrich_fills_missing_pets_from_description(self):
        """Should fill missing pets from description."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="2 bed apartment",
            price_cad=1850,
            bedrooms=2,
            description="Pets allowed",
            pets=None,
        )
        result = enrich(listing)
        assert result.pets == "allowed"

    def test_enrich_fills_missing_utilities_from_description(self):
        """Should fill missing utilities from description."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="2BR apartment",
            price_cad=1850,
            bedrooms=2,
            description="Utilities included",
            utilities=None,
        )
        result = enrich(listing)
        assert result.utilities == "included"

    def test_enrich_never_overwrites_existing_price(self):
        """Should never overwrite non-None price_cad."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="$2,000/mo apartment",  # Different price in title
            price_cad=1850,  # Existing value
        )
        result = enrich(listing)
        assert result.price_cad == 1850  # Should keep original

    def test_enrich_never_overwrites_existing_bedrooms(self):
        """Should never overwrite non-None bedrooms."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="3 bed apartment",  # Different bedrooms in title
            price_cad=1850,
            bedrooms=2,  # Existing value
        )
        result = enrich(listing)
        assert result.bedrooms == 2  # Should keep original

    def test_enrich_never_overwrites_any_field(self):
        """Should never overwrite any non-None field."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="$2,000/mo 3 bed basement apartment with shared laundry no parking",
            price_cad=1850,
            bedrooms=2,
            floor_level="main",
            laundry_inunit=True,
            parking_spots=1,
        )
        result = enrich(listing)
        assert result.price_cad == 1850
        assert result.bedrooms == 2
        assert result.floor_level == "main"
        assert result.laundry_inunit is True
        assert result.parking_spots == 1

    def test_enrich_uses_immutability(self):
        """Should return a new instance, not modify the original."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="$1,850/mo 2 bed apartment",
            price_cad=None,
            bedrooms=None,
        )
        original_price = listing.price_cad
        original_bedrooms = listing.bedrooms
        result = enrich(listing)
        # Original should be unchanged
        assert listing.price_cad == original_price
        assert listing.bedrooms == original_bedrooms
        # Result should have new values
        assert result.price_cad == 1850
        assert result.bedrooms == 2
        # Should be different instances
        assert result is not listing

    def test_enrich_concatenates_title_and_description(self):
        """Should concatenate title and description for parsing."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="2 bed apartment",
            price_cad=1850,
            bedrooms=2,
            description="with 1.5 bath",
            bathrooms=None,
        )
        result = enrich(listing)
        # Should find "1.5 bath" in description
        assert result.bathrooms == 1.5

    def test_enrich_handles_none_description(self):
        """Should handle None description gracefully."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="2 bed apartment",
            price_cad=1850,
            bedrooms=2,
            description=None,
        )
        result = enrich(listing)
        # Should not crash
        assert result.source == "kijiji"
        assert result.bedrooms == 2

    def test_enrich_preserves_all_fields(self):
        """Should preserve all fields including source, external_id, url."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="$1,850/mo 2 bed apartment",
            price_cad=None,
            bedrooms=None,
        )
        result = enrich(listing)
        assert result.source == "kijiji"
        assert result.external_id == "123"
        assert result.url == "https://example.com/123"

    def test_enrich_handles_empty_title(self):
        """Should handle empty title gracefully."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="",
            price_cad=None,
        )
        result = enrich(listing)
        assert result.source == "kijiji"
        assert result.price_cad is None

    def test_enrich_handles_empty_description(self):
        """Should handle empty description gracefully."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="2 bed apartment",
            price_cad=1850,
            bedrooms=2,
            description="",
        )
        result = enrich(listing)
        assert result.bedrooms == 2

    def test_enrich_returns_same_listing_when_all_fields_filled(self):
        """Should return equivalent listing when all fields already filled."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="$1,850/mo 2 bed apartment",
            price_cad=1850,
            bedrooms=2,
            city="Cambridge",
            floor_level="main",
            laundry_inunit=True,
            outdoor_space=True,
            parking_spots=2,
            pets="allowed",
            utilities="included",
            description="Nice apartment",
            bathrooms=1.5,
        )
        result = enrich(listing)
        # All fields should be unchanged
        assert result.price_cad == 1850
        assert result.bedrooms == 2
        assert result.city == "Cambridge"
        assert result.floor_level == "main"
        assert result.laundry_inunit is True
        assert result.outdoor_space is True
        assert result.parking_spots == 2
        assert result.pets == "allowed"
        assert result.utilities == "included"
        assert result.description == "Nice apartment"
        assert result.bathrooms == 1.5


class TestValidate:
    """Tests for validate() function."""

    def test_validate_rejects_none_price(self):
        """Should return False when price_cad is None."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="2BR apartment",
            price_cad=None,
        )
        result = validate(listing)
        assert result is False

    def test_validate_accepts_any_price(self):
        """Should return True for any non-None price."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="2BR apartment",
            price_cad=0,
        )
        result = validate(listing)
        assert result is True

    def test_validate_accepts_positive_price(self):
        """Should return True for positive price."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="2BR apartment",
            price_cad=1850,
        )
        result = validate(listing)
        assert result is True

    def test_validate_is_pure_function(self):
        """Should not modify the listing."""
        listing = RawListing(
            source="kijiji",
            external_id="123",
            url="https://example.com/123",
            title="2BR apartment",
            price_cad=1850,
        )
        original_price = listing.price_cad
        validate(listing)
        assert listing.price_cad == original_price
