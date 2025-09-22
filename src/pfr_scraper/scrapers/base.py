"""Base scaffolding shared by all scraper implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable

from pfr_scraper.http.fetch import fetch_html


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

        return fetch_html(self.endpoint)

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
