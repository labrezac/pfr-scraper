"""Scraper that captures team roster metadata for a given season."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Mapping, MutableMapping, Sequence

from bs4 import BeautifulSoup
from bs4.element import Tag

from pfr_scraper.http import build_session
from pfr_scraper.scrapers.base import Scraper
from pfr_scraper.settings import settings

BASE_URL = "https://www.pro-football-reference.com"

# PFR team abbreviations for current franchises.
DEFAULT_TEAM_CODES: tuple[str, ...] = (
    "crd",
    "atl",
    "rav",
    "buf",
    "car",
    "chi",
    "cin",
    "cle",
    "dal",
    "den",
    "det",
    "gnb",
    "htx",
    "clt",
    "jax",
    "kan",
    "rai",
    "sdg",
    "ram",
    "mia",
    "min",
    "nwe",
    "nor",
    "nyg",
    "nyj",
    "phi",
    "pit",
    "sfo",
    "sea",
    "tam",
    "oti",
    "was",
)


@dataclass(slots=True)
class TeamRosterRecord:
    """Structured data representing a team roster entry."""

    season: int
    team: str
    uniform_number: str | None
    player_id: str
    player_name: str
    player_url: str
    position: str | None
    age: str | None
    height: str | None
    weight: str | None
    experience: str | None
    games_played: str | None
    games_started: str | None
    approximate_value: str | None
    college: str | None
    birth_date: str | None
    draft_info: str | None


class TeamRosterScraper(Scraper):
    """Scrape team rosters for a specific season and export to CSV."""

    def __init__(
        self,
        *,
        season: int,
        teams: Sequence[str] | None = None,
    ) -> None:
        self.season = season
        self.teams: tuple[str, ...] = tuple(teams or DEFAULT_TEAM_CODES)
        self._latest_pages: MutableMapping[str, str] = {}

    @property
    def endpoint(self) -> str:
        return f"{BASE_URL}/teams/"

    def fetch(self) -> Mapping[str, str]:  # type: ignore[override]
        session = build_session()
        pages: dict[str, str] = {}
        try:
            for team in self.teams:
                url = f"{self.endpoint}{team}/{self.season}_roster.htm"
                response = session.get(url)
                response.raise_for_status()
                pages[team] = response.text
        finally:
            session.close()

        self._latest_pages = pages
        return pages

    def parse(self, payload: Mapping[str, str]) -> list[TeamRosterRecord]:  # type: ignore[override]
        records: list[TeamRosterRecord] = []
        for team, html in payload.items():
            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table", id="roster")
            if table is None:
                continue

            tbody = table.find("tbody")
            if tbody is None:
                continue

            for row in tbody.find_all("tr", recursive=False):
                if "class" in row.attrs and "thead" in row["class"]:
                    continue

                player_cell = row.find("td", attrs={"data-stat": "player"})
                if player_cell is None:
                    continue

                anchor = player_cell.find("a")
                if anchor is None or not anchor.get("href"):
                    continue

                player_name = anchor.get_text(strip=True)
                player_url = _resolve_url(anchor["href"])
                player_id = player_cell.get("data-append-csv") or _extract_player_id(anchor["href"])

                record = TeamRosterRecord(
                    season=self.season,
                    team=team,
                    uniform_number=_cell_text(row.find("th", attrs={"data-stat": "uniform_number"})),
                    player_id=player_id,
                    player_name=player_name,
                    player_url=player_url,
                    position=_cell_text(row.find("td", attrs={"data-stat": "pos"})),
                    age=_cell_text(row.find("td", attrs={"data-stat": "age"})),
                    height=_cell_text(row.find("td", attrs={"data-stat": "height"})),
                    weight=_cell_text(row.find("td", attrs={"data-stat": "weight"})),
                    experience=_cell_text(row.find("td", attrs={"data-stat": "experience"})),
                    games_played=_cell_text(row.find("td", attrs={"data-stat": "g"})),
                    games_started=_cell_text(row.find("td", attrs={"data-stat": "gs"})),
                    approximate_value=_cell_text(row.find("td", attrs={"data-stat": "av"})),
                    college=_cell_text(row.find("td", attrs={"data-stat": "college_id"})),
                    birth_date=_cell_text(row.find("td", attrs={"data-stat": "birth_date_mod"})),
                    draft_info=_cell_text(row.find("td", attrs={"data-stat": "draft_info"})),
                )
                records.append(record)

        return records

    def persist(self, records: Iterable[TeamRosterRecord]) -> None:  # type: ignore[override]
        processed_dir = settings.data_paths.processed
        processed_dir.mkdir(parents=True, exist_ok=True)
        output_path = processed_dir / f"team_rosters_{self.season}.csv"

        records_list = list(records)

        if records_list:
            import csv

            with output_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(asdict(records_list[0]).keys()))
                writer.writeheader()
                for item in records_list:
                    writer.writerow(asdict(item))
        else:
            # Ensure an empty file with headers exists for consistency.
            output_path.touch()

        # Persist raw HTML snapshots when available.
        if self._latest_pages:
            raw_dir = settings.data_paths.raw / "team_rosters" / str(self.season)
            raw_dir.mkdir(parents=True, exist_ok=True)
            for team, html in self._latest_pages.items():
                path = raw_dir / f"{team}.html"
                path.write_text(html, encoding="utf-8")


def _cell_text(cell: Tag | None) -> str | None:
    if cell is None:
        return None
    text = cell.get_text(" ", strip=True)
    return text or None


def _extract_player_id(href: str) -> str:
    filename = href.rstrip("/").split("/")[-1]
    return filename.split(".")[0]


def _resolve_url(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return f"{BASE_URL}{href}"


__all__ = ["TeamRosterScraper", "TeamRosterRecord", "DEFAULT_TEAM_CODES"]
