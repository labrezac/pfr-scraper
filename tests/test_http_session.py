"""Tests covering HTTP session configuration and emulator integration."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
import requests

from pfr_scraper.http import build_session
from pfr_scraper.settings import settings


class DummyRotator:
    def __init__(self) -> None:
        self.successes: list[str] = []
        self.failures: list[str] = []

    def record_success(self, profile_id: str) -> None:
        self.successes.append(profile_id)

    def record_failure(self, profile_id: str, *, sticky_key: Any | None = None) -> None:
        self.failures.append(profile_id)


class DummyProxyManager:
    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []

    def mark_success(self, proxy: Any) -> None:
        self.events.append(("success", proxy))

    def mark_failure(self, proxy: Any) -> None:
        self.events.append(("failure", proxy))


class DummyBuilder:
    def __init__(self, proxy_manager: DummyProxyManager | None = None) -> None:
        self.proxy_manager = proxy_manager


class DummyEmulator:
    def __init__(self, *, proxy: Any | None = None) -> None:
        self.rotator = DummyRotator()
        self.builder = DummyBuilder(proxy_manager=DummyProxyManager() if proxy else None)
        self._proxy = proxy

    def next_request(self) -> SimpleNamespace:
        return SimpleNamespace(
            headers={"X-Generated": "value", "User-Agent": "dummy-UA"},
            cookies={"session": "abc"},
            proxy=self._proxy,
            profile_id="profile-1",
        )


def test_build_session_merges_headers_and_records_success(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    def fake_request(self: requests.Session, method: str, url: str, **kwargs: Any) -> Any:
        captured.update(kwargs)

        class Response:
            status_code = 200

        return Response()

    monkeypatch.setattr(requests.Session, "request", fake_request, raising=False)

    original_headers = dict(settings.http.base_headers)
    original_cookies = dict(settings.http.cookies)
    settings.http.base_headers = {"X-Env": "env"}
    settings.http.cookies = {"cf_clearance": "token"}

    emulator = DummyEmulator()
    session = build_session(emulator=emulator, base_headers={"X-Base": "base"})

    session.get("https://example.com", headers={"X-Extra": "1"})

    headers = captured["headers"]
    assert headers["X-Base"] == "base"
    assert headers["X-Extra"] == "1"
    assert headers["X-Generated"] == "value"
    assert headers["User-Agent"] == "dummy-UA"
    assert headers["X-Env"] == "env"

    cookies = captured["cookies"]
    assert cookies["session"] == "abc"
    assert session.cookies.get("cf_clearance") == "token"

    assert captured["timeout"] == settings.request_timeout
    assert emulator.rotator.successes == ["profile-1"]
    assert emulator.rotator.failures == []

    settings.http.base_headers = original_headers
    settings.http.cookies = original_cookies


def test_build_session_records_failure_on_exception(monkeypatch: Any) -> None:
    def fake_request(self: requests.Session, method: str, url: str, **kwargs: Any) -> Any:
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(requests.Session, "request", fake_request, raising=False)

    emulator = DummyEmulator()
    session = build_session(emulator=emulator)

    with pytest.raises(requests.exceptions.Timeout):
        session.get("https://example.com")

    assert emulator.rotator.failures == ["profile-1"]
    assert emulator.rotator.successes == []


def test_build_session_applies_proxy_mapping(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    def fake_request(self: requests.Session, method: str, url: str, **kwargs: Any) -> Any:
        captured.update(kwargs)

        class Response:
            status_code = 200

        return Response()

    monkeypatch.setattr(requests.Session, "request", fake_request, raising=False)

    proxy = SimpleNamespace(url="http://proxy.local:8080")
    emulator = DummyEmulator(proxy=proxy)
    session = build_session(emulator=emulator)

    session.get("https://example.com")

    assert captured["proxies"] == {
        "http": proxy.url,
        "https": proxy.url,
    }
    assert emulator.builder.proxy_manager.events == [("success", proxy)]
