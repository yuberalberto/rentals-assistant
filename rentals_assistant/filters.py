from rentals_assistant.config import Settings
from rentals_assistant.models import RawListing


def passes_hard_filters(listing: RawListing, settings: Settings) -> bool:
    if listing.price_cad is not None and (listing.price_cad < settings.price_min or listing.price_cad > settings.price_max):
        return False
    if listing.bedrooms is not None and listing.bedrooms != settings.bedrooms:
        return False
    if listing.floor_level == "basement":
        return False
    if listing.laundry_inunit is not None and settings.laundry_required and not listing.laundry_inunit:
        return False
    if listing.parking_spots is not None and listing.parking_spots < settings.parking_min:
        return False
    return True
