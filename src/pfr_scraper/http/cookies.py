"""Utilities for seeding HTTP cookies from harvested data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping

from pfr_scraper.settings import settings

DEFAULT_COOKIE_PATH = Path("configs/cf_cookies.json")


def load_cookies_from_file(path: Path = DEFAULT_COOKIE_PATH) -> bool:
    """Load cookies from ``path`` into :mod:`settings.http`.

    Returns ``True`` if at least one cookie was applied, ``False`` otherwise.
    """

    if not path.exists():
        return False

    payload = json.loads(path.read_text(encoding="utf-8"))

    def _iter_cookies(data: object) -> Iterable[Mapping[str, str]]:
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and {"name", "value"} <= item.keys():
                    yield item  # type: ignore[return-value]
        elif isinstance(data, dict):
            # allow ``{"cookies": [...]}``
            inner = data.get("cookies")
            if isinstance(inner, list):
                yield from _iter_cookies(inner)

    applied = False
    for cookie in _iter_cookies(payload):
        settings.http.cookies[cookie["name"]] = cookie["value"]
        applied = True

    return applied


__all__ = ["load_cookies_from_file", "DEFAULT_COOKIE_PATH"]
