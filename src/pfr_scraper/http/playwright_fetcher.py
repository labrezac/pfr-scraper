"""Playwright-backed fetch helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pfr_scraper.settings import settings

DEFAULT_PROFILE_DIR = Path.home() / ".cache" / "pfr-playwright"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
)


def fetch_via_playwright(
    url: str,
    *,
    timeout: float = 45.0,
    profile_dir: Optional[Path] = None,
    headed: bool = False,
) -> str:
    """Fetch ``url`` using Playwright and return the rendered HTML."""

    try:
        from playwright.sync_api import Error, sync_playwright
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "playwright is required for browser-backed fetching. Install it with "
            "`pip install playwright` and run `playwright install chromium`."
        ) from exc

    profile_path = (profile_dir or settings.http.playwright_profile_dir or DEFAULT_PROFILE_DIR).expanduser()
    profile_path.mkdir(parents=True, exist_ok=True)

    launch_kwargs = dict(
        headless=not headed,
        user_agent=DEFAULT_USER_AGENT,
        locale="en-US",
        accept_downloads=False,
        bypass_csp=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    )

    with sync_playwright() as playwright:
        context = None
        try:
            context = playwright.chromium.launch_persistent_context(
                str(profile_path),
                channel="chrome",
                **launch_kwargs,
            )
        except Error:
            # Fallback to bundled Chromium if Chrome channel is unavailable.
            context = playwright.chromium.launch_persistent_context(
                str(profile_path),
                **launch_kwargs,
            )

        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        context.add_init_script(
            """
            Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});
            Object.defineProperty(navigator, 'platform', {get: () => 'MacIntel'});
            Object.defineProperty(navigator, 'language', {get: () => 'en-US'});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            """
        )

        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            try:
                page.wait_for_load_state("networkidle", timeout=timeout * 1000)
            except Error:
                pass
            page.wait_for_timeout(3_000)
            html = page.content()
        finally:
            context.close()

    return html


__all__ = ["fetch_via_playwright"]
