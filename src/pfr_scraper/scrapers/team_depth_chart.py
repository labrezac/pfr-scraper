"""Scraper that extracts team depth chart information for a season."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Mapping, MutableMapping, Sequence

from bs4 import BeautifulSoup
from bs4.element import Tag

from pfr_scraper.http import build_session
from pfr_scraper.scrapers.base import Scraper
from pfr_scraper.settings import settings

BASE_URL = "https://www.pro-football-reference.com"

DEPTH_CHART_TABLE_PREFIX = "depth_chart"


@dataclass(slots=True)
class TeamDepthChartRecord:
    """Normalized representation of a depth chart slot."""

    season: int
    team: str
    unit: str
    position: str
    depth_slot: int
    player_id: str | None
    player_name: str | None
    player_url: str | None
    note: str | None


class TeamDepthChartScraper(Scraper):
    """Scrape depth charts for teams in a given season."""

    def __init__(
        self,
        *,
        season: int,
        teams: Sequence[str],
    ) -> None:
        self.season = season
        self.teams: tuple[str, ...] = tuple(teams)
        self._latest_pages: MutableMapping[str, str] = {}

    @property
    def endpoint(self) -> str:
        return f"{BASE_URL}/teams/"

    def fetch(self) -> Mapping[str, str]:  # type: ignore[override]
        session = build_session()
        pages: dict[str, str] = {}
        try:
            for team in self.teams:
                url = f"{self.endpoint}{team}/{self.season}_depth_chart.htm"
                response = session.get(url)
                response.raise_for_status()
                pages[team] = response.text
        finally:
            session.close()

        self._latest_pages = pages
        return pages

    def parse(self, payload: Mapping[str, str]) -> list[TeamDepthChartRecord]:  # type: ignore[override]
        records: list[TeamDepthChartRecord] = []
        for team, html in payload.items():
            soup = BeautifulSoup(html, "html.parser")
            for table in soup.find_all("table"):
                table_id = table.get("id", "")
                if not table_id.startswith(DEPTH_CHART_TABLE_PREFIX):
                    continue

                unit = _unit_from_table_id(table_id)
                tbody = table.find("tbody")
                if tbody is None:
                    continue

                for row in tbody.find_all("tr", recursive=False):
                    if "class" in row.attrs and "thead" in row["class"]:
                        continue

                    position_cell = row.find("th", scope="row")
                    if position_cell is None:
                        continue

                    position = position_cell.get_text(strip=True)
                    slot_cells = row.find_all("td", recursive=False)
                    for slot_index, cell in enumerate(slot_cells, start=1):
                        cell_records = _records_from_cell(
                            season=self.season,
                            team=team,
                            unit=unit,
                            position=position,
                            depth_slot=slot_index,
                            cell=cell,
                        )
                        records.extend(cell_records)

        return records

    def persist(self, records: Iterable[TeamDepthChartRecord]) -> None:  # type: ignore[override]
        processed_dir = settings.data_paths.processed
        processed_dir.mkdir(parents=True, exist_ok=True)
        output_path = processed_dir / f"team_depth_chart_{self.season}.csv"

        records_list = list(records)

        if records_list:
            import csv

            with output_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(asdict(records_list[0]).keys()))
                writer.writeheader()
                for item in records_list:
                    writer.writerow(asdict(item))
        else:
            output_path.touch()

        if self._latest_pages:
            raw_dir = settings.data_paths.raw / "team_depth_charts" / str(self.season)
            raw_dir.mkdir(parents=True, exist_ok=True)
            for team, html in self._latest_pages.items():
                path = raw_dir / f"{team}.html"
                path.write_text(html, encoding="utf-8")


def _records_from_cell(
    *,
    season: int,
    team: str,
    unit: str,
    position: str,
    depth_slot: int,
    cell: Tag,
) -> list[TeamDepthChartRecord]:
    anchors = cell.find_all("a")
    cell_text = cell.get_text(" ", strip=True)

    if anchors:
        note = _derive_note(cell_text, [anchor.get_text(strip=True) for anchor in anchors])
        records: list[TeamDepthChartRecord] = []
        for anchor in anchors:
            href = anchor.get("href")
            player_name = anchor.get_text(strip=True)
            player_id = _extract_player_id(href) if href else None
            player_url = _resolve_url(href) if href else None
            records.append(
                TeamDepthChartRecord(
                    season=season,
                    team=team,
                    unit=unit,
                    position=position,
                    depth_slot=depth_slot,
                    player_id=player_id,
                    player_name=player_name or None,
                    player_url=player_url,
                    note=note,
                )
            )
        return records

    if cell_text:
        return [
            TeamDepthChartRecord(
                season=season,
                team=team,
                unit=unit,
                position=position,
                depth_slot=depth_slot,
                player_id=None,
                player_name=cell_text,
                player_url=None,
                note=None,
            )
        ]

    return []


def _derive_note(cell_text: str, anchor_texts: list[str]) -> str | None:
    remainder = cell_text
    for text in anchor_texts:
        remainder = remainder.replace(text, "", 1).strip()
    return remainder or None


def _unit_from_table_id(table_id: str) -> str:
    suffix = table_id.replace(DEPTH_CHART_TABLE_PREFIX, "", 1).strip("_")
    mapping = {
        "offense": "Offense",
        "defense": "Defense",
        "special_teams": "Special Teams",
    }
    return mapping.get(suffix, suffix.title() if suffix else "Depth Chart")


def _extract_player_id(href: str | None) -> str | None:
    if not href:
        return None
    filename = href.rstrip("/").split("/")[-1]
    return filename.split(".")[0] if filename else None


def _resolve_url(href: str | None) -> str | None:
    if not href:
        return None
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return f"{BASE_URL}{href}"


__all__ = ["TeamDepthChartScraper", "TeamDepthChartRecord"]
