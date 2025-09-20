"""Tests for the TeamGameLogScraper implementation."""

from __future__ import annotations

import csv
from textwrap import dedent
from typing import Any

from pfr_scraper.scrapers.team_game_logs import TeamGameLogScraper
from pfr_scraper.settings import settings

SAMPLE_GAME_LOG_HTML = dedent(
    """
    <div>
        <table id="table_pfr_team-year_game-logs_team-year-regular-season-game-log">
            <tbody>
                <tr>
                    <th data-stat="ranker">1</th>
                    <td data-stat="team_game_num_season">1</td>
                    <td data-stat="week_num">1</td>
                    <td data-stat="date"><a href="/boxscores/202409080chi.htm">2024-09-08</a></td>
                    <td data-stat="game_day_of_week">Sun</td>
                    <td data-stat="game_location">@</td>
                    <td data-stat="opp_name_abbr">CHI</td>
                    <td data-stat="team_game_result">W</td>
                    <td data-stat="points">24</td>
                    <td data-stat="points_opp">17</td>
                    <td data-stat="overtimes"></td>
                </tr>
                <tr class="thead"><th data-stat="ranker">Totals</th></tr>
            </tbody>
        </table>
        <table id="table_pfr_team-year_game-logs_team-year-playoffs-game-log">
            <tbody>
                <tr>
                    <th data-stat="ranker">2</th>
                    <td data-stat="team_game_num_season">18</td>
                    <td data-stat="week_num">Division</td>
                    <td data-stat="date"><a href="/boxscores/202501120sfo.htm">2025-01-12</a></td>
                    <td data-stat="game_day_of_week">Sun</td>
                    <td data-stat="game_location">N</td>
                    <td data-stat="opp_name_abbr">DAL</td>
                    <td data-stat="team_game_result">L</td>
                    <td data-stat="points">20</td>
                    <td data-stat="points_opp">24</td>
                    <td data-stat="overtimes">OT</td>
                </tr>
            </tbody>
        </table>
    </div>
    """
)


class StubResponse:
    def __init__(self, payload: str) -> None:
        self.text = payload

    def raise_for_status(self) -> None:  # pragma: no cover - simple stub
        return None


class StubSession:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.closed = False

    def get(self, url: str, **_: Any) -> StubResponse:
        self.calls.append(url)
        return StubResponse(SAMPLE_GAME_LOG_HTML)

    def close(self) -> None:
        self.closed = True


def test_team_game_log_scraper(tmp_path, monkeypatch) -> None:
    stub_session = StubSession()
    monkeypatch.setattr(
        "pfr_scraper.scrapers.team_game_logs.build_session",
        lambda: stub_session,
    )

    original_root = settings.data_paths.root
    settings.data_paths.root = tmp_path

    try:
        scraper = TeamGameLogScraper(season=2024, teams=("sfo",))
        records = scraper.run()
    finally:
        settings.data_paths.root = original_root

    assert stub_session.calls == [
        "https://www.pro-football-reference.com/teams/sfo/2024/gamelog/",
    ]
    assert stub_session.closed is True

    assert len(records) == 2

    regular = next(record for record in records if record.game_type == "regular")
    assert regular.boxscore_url == "https://www.pro-football-reference.com/boxscores/202409080chi.htm"
    assert regular.home_away == "@"
    assert regular.opponent == "CHI"
    assert regular.team_points == "24"

    playoff = next(record for record in records if record.game_type == "playoffs")
    assert playoff.week == "Division"
    assert playoff.overtime == "OT"

    processed_path = tmp_path / "processed" / "team_game_logs_2024.csv"
    assert processed_path.exists()

    with processed_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert rows[0]["team"] == "sfo"
    assert {row["game_type"] for row in rows} == {"regular", "playoffs"}

    raw_snapshot = tmp_path / "raw" / "team_game_logs" / "2024" / "sfo.html"
    assert raw_snapshot.exists()
