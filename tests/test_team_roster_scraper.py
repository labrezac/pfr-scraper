"""Tests for the TeamRosterScraper implementation."""

from __future__ import annotations

import csv
from textwrap import dedent
from typing import Any

from pfr_scraper.scrapers.team_rosters import TeamRosterScraper
from pfr_scraper.settings import settings

SAMPLE_ROSTER_HTML = dedent(
    """
    <table id="roster">
        <tbody>
            <tr>
                <th data-stat="uniform_number">11</th>
                <td data-stat="player" data-append-csv="TestPl00"><a href="/players/T/TestPl00.htm">Test Player</a></td>
                <td data-stat="age">25</td>
                <td data-stat="pos">QB</td>
                <td data-stat="g">17</td>
                <td data-stat="gs">17</td>
                <td data-stat="weight">210</td>
                <td data-stat="height">6-2</td>
                <td data-stat="college_id">Test College</td>
                <td data-stat="birth_date_mod">1/1/1999</td>
                <td data-stat="experience">3</td>
                <td data-stat="av">12</td>
                <td data-stat="draft_info">Team / 1st / 10th pick / 2021</td>
            </tr>
            <tr>
                <th data-stat="uniform_number">99</th>
                <td data-stat="player" data-append-csv="OtherPl00"><a href="/players/O/OtherPl00.htm">Other Player</a></td>
                <td data-stat="age"></td>
                <td data-stat="pos">DL</td>
                <td data-stat="g">16</td>
                <td data-stat="gs">8</td>
                <td data-stat="weight">300</td>
                <td data-stat="height">6-5</td>
                <td data-stat="college_id">Another College</td>
                <td data-stat="birth_date_mod"></td>
                <td data-stat="experience">5</td>
                <td data-stat="av">7</td>
                <td data-stat="draft_info">Undrafted</td>
            </tr>
        </tbody>
    </table>
    """
)


class StubResponse:
    def __init__(self, payload: str) -> None:
        self.text = payload

    def raise_for_status(self) -> None:
        return None


class StubSession:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.closed = False

    def get(self, url: str, **_: Any) -> StubResponse:
        self.calls.append(url)
        return StubResponse(SAMPLE_ROSTER_HTML)

    def close(self) -> None:
        self.closed = True


def test_team_roster_scraper(tmp_path, monkeypatch) -> None:
    stub_session = StubSession()
    monkeypatch.setattr(
        "pfr_scraper.scrapers.team_rosters.build_session",
        lambda: stub_session,
    )

    original_root = settings.data_paths.root
    settings.data_paths.root = tmp_path

    try:
        scraper = TeamRosterScraper(season=2024, teams=("sfo",))
        records = scraper.run()
    finally:
        settings.data_paths.root = original_root

    assert stub_session.calls == [
        "https://www.pro-football-reference.com/teams/sfo/2024_roster.htm",
    ]
    assert stub_session.closed is True

    assert len(records) == 2
    first = records[0]
    assert first.player_id == "TestPl00"
    assert first.player_name == "Test Player"
    assert first.position == "QB"
    assert first.uniform_number == "11"

    processed_path = tmp_path / "processed" / "team_rosters_2024.csv"
    assert processed_path.exists()

    with processed_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert rows[0]["player_id"] == "TestPl00"
    assert rows[0]["draft_info"] == "Team / 1st / 10th pick / 2021"

    raw_snapshot = tmp_path / "raw" / "team_rosters" / "2024" / "sfo.html"
    assert raw_snapshot.exists()
