"""Tests for the TeamDepthChartScraper implementation."""

from __future__ import annotations

import csv
from textwrap import dedent
from typing import Any

from pfr_scraper.scrapers.team_depth_chart import TeamDepthChartScraper
from pfr_scraper.settings import settings

SAMPLE_DEPTH_CHART_HTML = dedent(
    """
    <table id="depth_chart_offense">
        <tbody>
            <tr>
                <th scope="row">QB</th>
                <td><a href="/players/Q/QbOne00.htm">QB One</a></td>
                <td><a href="/players/Q/QbTwo00.htm">QB Two</a> (PS)</td>
            </tr>
            <tr>
                <th scope="row">WR</th>
                <td><a href="/players/W/WrOne00.htm">WR One</a></td>
                <td>Injured</td>
            </tr>
        </tbody>
    </table>
    <table id="depth_chart_defense">
        <tbody>
            <tr>
                <th scope="row">CB</th>
                <td><a href="/players/C/CbOne00.htm">CB One</a></td>
                <td><a href="/players/C/CbTwo00.htm">CB Two</a></td>
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
        return StubResponse(SAMPLE_DEPTH_CHART_HTML)

    def close(self) -> None:
        self.closed = True


def test_team_depth_chart_scraper(tmp_path, monkeypatch) -> None:
    stub_session = StubSession()
    monkeypatch.setattr(
        "pfr_scraper.scrapers.team_depth_chart.build_session",
        lambda: stub_session,
    )

    original_root = settings.data_paths.root
    settings.data_paths.root = tmp_path

    try:
        scraper = TeamDepthChartScraper(season=2024, teams=("sfo",))
        records = scraper.run()
    finally:
        settings.data_paths.root = original_root

    assert stub_session.calls == [
        "https://www.pro-football-reference.com/teams/sfo/2024_depth_chart.htm",
    ]
    assert stub_session.closed is True

    assert len(records) == 6

    players = {(record.position, record.depth_slot, record.player_name): record for record in records}

    assert ("QB", 1, "QB One") in players
    second_qb = players[("QB", 2, "QB Two")]
    assert second_qb.note == "(PS)"
    assert second_qb.player_id == "QbTwo00"

    injured_slot = players[("WR", 2, "Injured")]
    assert injured_slot.player_id is None

    processed_path = tmp_path / "processed" / "team_depth_chart_2024.csv"
    assert processed_path.exists()

    with processed_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert any(row["player_name"] == "CB One" and row["unit"] == "Defense" for row in rows)

    raw_snapshot = tmp_path / "raw" / "team_depth_charts" / "2024" / "sfo.html"
    assert raw_snapshot.exists()
