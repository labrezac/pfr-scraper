"""Harvest Cloudflare clearance cookies via Playwright."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from playwright.sync_api import Error, sync_playwright

DEFAULT_URL = "https://www.pro-football-reference.com/players/A/"
DEFAULT_OUTPUT = Path("configs/cf_cookies.json")
DEFAULT_PROFILE_DIR = Path.home() / ".cache" / "pfr-playwright"


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="Page to visit while solving the Cloudflare challenge.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to write harvested cookies (JSON list).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=45.0,
        help="Seconds to wait for the page to finish loading after navigation.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Launch Chromium in headed mode to manually solve challenges if needed.",
    )
    parser.add_argument(
        "--profile-dir",
        type=Path,
        default=DEFAULT_PROFILE_DIR,
        help="Directory used for the persistent Chromium profile (improves stealth).",
    )
    parser.add_argument(
        "--extend",
        action="store_true",
        help=(
            "Keep existing cookies in configs/cf_cookies.json and layer new ones. "
            "Useful when manually assembling the clearance bundle."
        ),
    )
    return parser.parse_args(argv)


def harvest(url: str, output: Path, timeout: float, headed: bool, profile_dir: Path, extend: bool) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    profile_dir = profile_dir.expanduser()
    profile_dir.mkdir(parents=True, exist_ok=True)

    user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    )

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(profile_dir),
            headless=not headed,
            user_agent=user_agent,
            locale="en-US",
            bypass_csp=True,
            accept_downloads=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
            extra_http_headers={
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9," "image/avif,image/webp,image/apng,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
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
            page.wait_for_load_state("networkidle", timeout=timeout * 1000)
        except Error:
            # Cloudflare may still complete after DOMContentLoaded; ignore timeout.
            pass

        page.wait_for_timeout(3_000)

        if headed:
            print("Press Enter once the page finishes loading...")
            try:
                input()
            except EOFError:
                pass

        cookies: list[dict[str, object]] = []
        has_clearance = False
        for _ in range(15):  # poll for up to ~15 seconds
            cookies = [
                cookie
                for cookie in context.cookies(url)
                if cookie["domain"].endswith("pro-football-reference.com")
            ]
            has_clearance = any(cookie["name"] == "cf_clearance" for cookie in cookies)
            if has_clearance:
                break
            page.wait_for_timeout(1_000)

        if not cookies or not has_clearance:
            context.close()
            names = ", ".join(sorted({cookie["name"] for cookie in cookies}))
            print(
                "No Cloudflare clearance cookie captured; rerun (optionally with --headed).",
                file=sys.stderr,
            )
            if cookies:
                print(f"Captured cookies: {names}", file=sys.stderr)
            return 1

        if extend and output.exists():
            existing = json.loads(output.read_text(encoding="utf-8"))
            existing_map = {item["name"]: item for item in existing if isinstance(item, dict)}
            existing_map.update({cookie["name"]: cookie for cookie in cookies})
            cookies = list(existing_map.values())  # type: ignore[assignment]

        output.write_text(json.dumps(cookies, indent=2), encoding="utf-8")
        context.close()

    print(f"Captured {len(cookies)} cookies -> {output}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    return harvest(args.url, args.output, args.timeout, args.headed, args.profile_dir, args.extend)


if __name__ == "__main__":
    raise SystemExit(main())
