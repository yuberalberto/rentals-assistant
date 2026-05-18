from dataclasses import replace

from rentals_assistant.models import RawListing
from rentals_assistant.scrapers.parsers import (
    parse_bathrooms,
    parse_bedrooms,
    parse_floor_level,
    parse_laundry,
    parse_outdoor_space,
    parse_parking,
    parse_pets,
    parse_price,
    parse_utilities,
)


def enrich(listing: RawListing) -> RawListing:
    """Fill missing fields from title and description.

    Concatenates title and description, then re-parses using all shared parsers.
    Only fills fields that are None (never overwrites existing values).
    Returns a new RawListing instance (immutable).

    Args:
        listing: RawListing to enrich

    Returns:
        New RawListing with missing fields filled from title+description
    """
    text = f"{listing.title} {(listing.description or '')}"

    updates = {}
    if listing.price_cad is None:
        updates["price_cad"] = parse_price(text)
    if listing.bedrooms is None:
        updates["bedrooms"] = parse_bedrooms(text)
    if listing.bathrooms is None:
        updates["bathrooms"] = parse_bathrooms(text)
    if listing.floor_level is None:
        updates["floor_level"] = parse_floor_level(text)
    if listing.laundry_inunit is None:
        updates["laundry_inunit"] = parse_laundry(text)
    if listing.outdoor_space is None:
        updates["outdoor_space"] = parse_outdoor_space(text)
    if listing.parking_spots is None:
        updates["parking_spots"] = parse_parking(text)
    if listing.pets is None:
        updates["pets"] = parse_pets(text)
    if listing.utilities is None:
        updates["utilities"] = parse_utilities(text)

    return replace(listing, **updates)


def validate(listing: RawListing) -> bool:
    """Validate that listing has required fields.

    Returns False if price_cad is None (price is mandatory).
    Returns True otherwise.

    Args:
        listing: RawListing to validate

    Returns:
        True if listing is valid, False otherwise
    """
    return listing.price_cad is not None
