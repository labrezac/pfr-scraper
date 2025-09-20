"""Scraper that extracts all active NFL players from Pro-Football-Reference."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Mapping, Sequence

from bs4 import BeautifulSoup
from bs4.element import Tag

from pfr_scraper.http import build_session
from pfr_scraper.scrapers.base import Scraper
from pfr_scraper.settings import settings

BASE_URL = "https://www.pro-football-reference.com"


@dataclass(slots=True)
class ActivePlayerRecord:
    """Structured representation of an active player's metadata."""

    player_id: str
    player_name: str
    letter: str
    url: str
    position: str | None


class ActivePlayersScraper(Scraper):
    """Scrape every active player index page and persist the results as CSV."""

    def __init__(self, *, letters: Sequence[str] | None = None) -> None:
        self.letters: tuple[str, ...] = tuple(
            letter.upper() for letter in (letters or tuple(chr(i) for i in range(ord("A"), ord("Z") + 1)))
        )

    @property
    def endpoint(self) -> str:
        # Base index page; individual letter pages live beneath this path.
        return f"{BASE_URL}/players/"

    def fetch(self) -> Mapping[str, str]:  # type: ignore[override]
        """Retrieve HTML for each letter-specific player index page."""

        session = build_session()
        responses: dict[str, str] = {}
        try:
            for letter in self.letters:
                url = f"{self.endpoint}{letter}/"
                response = session.get(url)
                response.raise_for_status()
                responses[letter] = response.text
        finally:
            session.close()
        return responses

    def parse(self, payload: Mapping[str, str]) -> List[ActivePlayerRecord]:  # type: ignore[override]
        """Extract active player metadata from each letter page."""

        records: dict[str, ActivePlayerRecord] = {}
        for letter, html in payload.items():
            soup = BeautifulSoup(html, "html.parser")
            container = soup.find("div", id="div_players")
            if container is None:
                continue

            for bold in container.find_all("b"):
                anchor = bold.find("a")
                if anchor is None or not anchor.get("href"):
                    continue

                name = anchor.get_text(strip=True)
                href = anchor["href"]
                player_id = _extract_player_id(href)
                full_url = _resolve_url(href)

                position = _extract_position(bold, name)

                # Deduplicate based on player id in case pages overlap unexpectedly.
                records[player_id] = ActivePlayerRecord(
                    player_id=player_id,
                    player_name=name,
                    letter=letter,
                    url=full_url,
                    position=position,
                )

        # Sort for deterministic output (alphabetical by letter then name).
        return sorted(records.values(), key=lambda record: (record.letter, record.player_name))

    def persist(self, records: Iterable[ActivePlayerRecord]) -> None:  # type: ignore[override]
        """Write the extracted player list to the processed data directory."""

        processed_dir = settings.data_paths.processed
        processed_dir.mkdir(parents=True, exist_ok=True)
        output_path = processed_dir / "active_players.csv"

        fieldnames = ["player_id", "player_name", "letter", "url", "position"]

        import csv

        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow(
                    {
                        "player_id": record.player_id,
                        "player_name": record.player_name,
                        "letter": record.letter,
                        "url": record.url,
                        "position": record.position or "",
                    }
                )


def _extract_player_id(href: str) -> str:
    filename = href.rstrip("/").split("/")[-1]
    return filename.removesuffix(".htm")


def _resolve_url(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return f"{BASE_URL}{href}"


def _extract_position(bold_tag: Tag, player_name: str) -> str | None:
    """Return the position text that follows the anchor within the bold tag."""

    bold_text = bold_tag.get_text(" ", strip=True)
    suffix = bold_text[len(player_name) :].strip()
    if suffix.startswith("(") and suffix.endswith(")"):
        return suffix[1:-1].strip() or None
    return None


__all__ = ["ActivePlayersScraper", "ActivePlayerRecord"]
