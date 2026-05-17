from rentals_assistant.models import RawListing


def passes_hard_filters(listing: RawListing) -> bool:
    if listing.price_cad is not None and listing.price_cad > 2000:
        return False
    if listing.bedrooms is not None and listing.bedrooms != 2:
        return False
    if listing.floor_level == "basement":
        return False
    if listing.pets == "not_allowed":
        return False
    if listing.laundry_inunit is not None and not listing.laundry_inunit:
        return False
    if listing.parking_spots is not None and listing.parking_spots < 1:  # noqa: SIM103
        return False
    return True
