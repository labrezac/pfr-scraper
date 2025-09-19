"""Base scaffolding shared by all scraper implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable

from pfr_scraper.http import build_session


class Scraper(ABC):
    """Template method for concrete scrapers."""

    def run(self) -> Iterable[Any]:
        """Execute the scraper and yield parsed records."""

        raw_payload = self.fetch()
        records = self.parse(raw_payload)
        self.persist(records)
        return records

    def fetch(self) -> Any:
        """Retrieve remote data.

        Subclasses may override this to customise HTTP access while still
        benefiting from the shared header emulator integration.
        """

        session = build_session()
        response = session.get(self.endpoint)
        response.raise_for_status()
        return response

    @property
    @abstractmethod
    def endpoint(self) -> str:
        """The resource URL to pull."""

    @abstractmethod
    def parse(self, payload: Any) -> Iterable[Any]:
        """Convert raw payloads into structured records."""

    def persist(self, records: Iterable[Any]) -> None:
        """Hook for saving records. Default implementation is a no-op."""

        return None
