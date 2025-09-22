"""Utilities for fetching HTML with graceful fallbacks."""

from __future__ import annotations

from typing import Optional

import requests
from requests import Session
from requests.exceptions import HTTPError

from pfr_scraper.http import build_session
from pfr_scraper.http.playwright_fetcher import fetch_via_playwright


def fetch_html(url: str, *, session: Optional[Session] = None, timeout: Optional[float] = None) -> str:
    """Retrieve HTML for ``url`` using requests, falling back to Playwright on 403."""

    owns_session = session is None
    sess = session or build_session()
    try:
        response = sess.get(url, timeout=timeout)
        try:
            response.raise_for_status()
        except HTTPError as exc:
            if response.status_code == 403:
                return fetch_via_playwright(url)
            raise exc
        return response.text
    finally:
        if owns_session:
            sess.close()


__all__ = ["fetch_html"]
