"""Registry of all available scrapers for the pipeline."""

from rentals_assistant.scrapers.activa import ActivaScraper
from rentals_assistant.scrapers.craigslist import CraigslistScraper
from rentals_assistant.scrapers.kijiji import KijijiScraper
from rentals_assistant.scrapers.kw_property import KwPropertyScraper
from rentals_assistant.scrapers.liv_rent import LivRentScraper
from rentals_assistant.scrapers.padmapper import PadMapperScraper
from rentals_assistant.scrapers.rentals_ca import RentalsCaScraper
from rentals_assistant.scrapers.viewit import ViewItScraper
from rentals_assistant.scrapers.zumper import ZumperScraper


def build_scrapers() -> list:
    """Instantiate and return all available scrapers.

    Returns:
        List of scraper instances ready for pipeline.run().
    """
    return [
        ActivaScraper(),
        CraigslistScraper(),
        KijijiScraper(),
        KwPropertyScraper(),
        LivRentScraper(),
        PadMapperScraper(),
        RentalsCaScraper(),
        ViewItScraper(),
        ZumperScraper(),
    ]
