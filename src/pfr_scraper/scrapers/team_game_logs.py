"""Scraper that normalizes team game logs for a season."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Mapping, MutableMapping, Sequence

from bs4 import BeautifulSoup
from bs4.element import Tag

from pfr_scraper.http import build_session
from pfr_scraper.scrapers.base import Scraper
from pfr_scraper.settings import settings

BASE_URL = "https://www.pro-football-reference.com"

GAME_TABLES: Mapping[str, str] = {
    "table_pfr_team-year_game-logs_team-year-regular-season-game-log": "regular",
    "table_pfr_team-year_game-logs_team-year-playoffs-game-log": "playoffs",
}

STAT_FIELDS: Mapping[str, str] = {
    "team_game_num_season": "game_number",
    "week_num": "week",
    "date": "date",
    "game_day_of_week": "day",
    "game_location": "home_away",
    "opp_name_abbr": "opponent",
    "team_game_result": "result",
    "points": "team_points",
    "points_opp": "opponent_points",
    "overtimes": "overtime",
}


@dataclass(slots=True)
class TeamGameLogRecord:
    """Structured summary of a single team game log entry."""

    season: int
    team: str
    game_type: str
    game_number: str | None
    week: str | None
    date: str | None
    day: str | None
    home_away: str | None
    opponent: str | None
    result: str | None
    team_points: str | None
    opponent_points: str | None
    overtime: str | None
    boxscore_url: str | None


class TeamGameLogScraper(Scraper):
    """Scrape game logs for teams in a specific season."""

    def __init__(
        self,
        *,
        season: int,
        teams: Sequence[str],
        include_playoffs: bool = True,
    ) -> None:
        self.season = season
        self.teams: tuple[str, ...] = tuple(teams)
        self.include_playoffs = include_playoffs
        self._latest_pages: MutableMapping[str, str] = {}

    @property
    def endpoint(self) -> str:
        return f"{BASE_URL}/teams/"

    def fetch(self) -> Mapping[str, str]:  # type: ignore[override]
        session = build_session()
        pages: dict[str, str] = {}
        try:
            for team in self.teams:
                url = f"{self.endpoint}{team}/{self.season}/gamelog/"
                response = session.get(url)
                response.raise_for_status()
                pages[team] = response.text
        finally:
            session.close()

        self._latest_pages = pages
        return pages

    def parse(self, payload: Mapping[str, str]) -> list[TeamGameLogRecord]:  # type: ignore[override]
        records: list[TeamGameLogRecord] = []
        table_ids = GAME_TABLES.items()

        for team, html in payload.items():
            soup = BeautifulSoup(html, "html.parser")
            for table_id, game_type in table_ids:
                if not self.include_playoffs and game_type == "playoffs":
                    continue
                table = soup.find("table", id=table_id)
                if table is None:
                    continue
                tbody = table.find("tbody")
                if tbody is None:
                    continue
                for row in tbody.find_all("tr", recursive=False):
                    if _is_header_row(row):
                        continue
                    record = _row_to_record(
                        row=row,
                        season=self.season,
                        team=team,
                        game_type=game_type,
                    )
                    if record is not None:
                        records.append(record)

        return records

    def persist(self, records: Iterable[TeamGameLogRecord]) -> None:  # type: ignore[override]
        processed_dir = settings.data_paths.processed
        processed_dir.mkdir(parents=True, exist_ok=True)
        output_path = processed_dir / f"team_game_logs_{self.season}.csv"

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
            raw_dir = settings.data_paths.raw / "team_game_logs" / str(self.season)
            raw_dir.mkdir(parents=True, exist_ok=True)
            for team, html in self._latest_pages.items():
                path = raw_dir / f"{team}.html"
                path.write_text(html, encoding="utf-8")


def _row_to_record(
    *,
    row: Tag,
    season: int,
    team: str,
    game_type: str,
) -> TeamGameLogRecord | None:
    values: dict[str, str | None] = {
        "season": season,
        "team": team,
        "game_type": game_type,
        "boxscore_url": None,
    }

    has_opponent = False

    for cell in row.find_all(["th", "td"], recursive=False):
        stat = cell.get("data-stat")
        if stat in STAT_FIELDS:
            key = STAT_FIELDS[stat]
            values[key] = _cell_text(cell)
            if key == "opponent" and values[key]:
                has_opponent = True
        if stat == "date":
            anchor = cell.find("a")
            if anchor and anchor.get("href"):
                values["boxscore_url"] = _resolve_url(anchor["href"])

    if not has_opponent:
        return None

    return TeamGameLogRecord(
        season=values["season"],
        team=values["team"],
        game_type=values["game_type"],
        game_number=values.get("game_number"),
        week=values.get("week"),
        date=values.get("date"),
        day=values.get("day"),
        home_away=values.get("home_away"),
        opponent=values.get("opponent"),
        result=values.get("result"),
        team_points=values.get("team_points"),
        opponent_points=values.get("opponent_points"),
        overtime=values.get("overtime"),
        boxscore_url=values.get("boxscore_url"),
    )


def _is_header_row(row: Tag) -> bool:
    classes = row.get("class") or []
    return "thead" in classes or "partial_table" in classes


def _cell_text(cell: Tag) -> str | None:
    text = cell.get_text(" ", strip=True)
    return text or None


def _resolve_url(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return f"{BASE_URL}{href}"


__all__ = ["TeamGameLogScraper", "TeamGameLogRecord"]
