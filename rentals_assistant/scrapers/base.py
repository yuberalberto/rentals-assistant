from abc import ABC, abstractmethod

from rentals_assistant.models import RawListing


class Scraper(ABC):
    @abstractmethod
    async def fetch(self) -> list[RawListing]:
        ...
