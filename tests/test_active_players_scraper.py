"""Tests for the ActivePlayersScraper implementation."""

from __future__ import annotations

import csv
from textwrap import dedent
from typing import Any

import requests

from pfr_scraper.scrapers.active_players import ActivePlayersScraper
from pfr_scraper.settings import settings

SAMPLE_HTML = dedent(
    """
    <div id="div_players">
        <p><b><a href="/players/A/TestPl00.htm">Test Player</a> (QB)</b> 2023-2025</p>
        <p><a href="/players/A/OtherPl00.htm">Other Player</a> (RB) 2019-2020</p>
        <p><b><a href="/players/A/ProxyPl01.htm">Proxy Player</a></b> 2022-2024</p>
    </div>
    """
)


class StubResponse:
    def __init__(self, payload: str, status_code: int = 200) -> None:
        self.text = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class StubSession:
    def __init__(self) -> None:
        self.closed = False
        self.calls: list[str] = []

    def get(self, url: str, **_: Any) -> StubResponse:
        self.calls.append(url)
        return StubResponse(SAMPLE_HTML)

    def close(self) -> None:
        self.closed = True


def test_active_players_scraper_run(tmp_path, monkeypatch) -> None:
    stub_session = StubSession()

    monkeypatch.setattr(
        "pfr_scraper.scrapers.active_players.build_session",
        lambda: stub_session,
    )

    original_root = settings.data_paths.root
    settings.data_paths.root = tmp_path

    try:
        scraper = ActivePlayersScraper(letters=("A",))
        records = scraper.run()
    finally:
        settings.data_paths.root = original_root

    assert stub_session.calls == [
        "https://www.pro-football-reference.com/players/A/",
    ]
    assert stub_session.closed is True

    assert len(records) == 2
    records_by_id = {record.player_id: record for record in records}
    assert set(records_by_id.keys()) == {"TestPl00", "ProxyPl01"}

    first = records_by_id["TestPl00"]
    assert first.player_name == "Test Player"
    assert first.letter == "A"
    assert first.url == "https://www.pro-football-reference.com/players/A/TestPl00.htm"
    assert first.position == "QB"

    second = records_by_id["ProxyPl01"]
    assert second.position is None

    output_path = tmp_path / "processed" / "active_players.csv"
    assert output_path.exists()

    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    rows_by_id = {row["player_id"]: row for row in rows}

    assert rows_by_id == {
        "TestPl00": {
            "player_id": "TestPl00",
            "player_name": "Test Player",
            "letter": "A",
            "url": "https://www.pro-football-reference.com/players/A/TestPl00.htm",
            "position": "QB",
        },
        "ProxyPl01": {
            "player_id": "ProxyPl01",
            "player_name": "Proxy Player",
            "letter": "A",
            "url": "https://www.pro-football-reference.com/players/A/ProxyPl01.htm",
            "position": "",
        },
    }
