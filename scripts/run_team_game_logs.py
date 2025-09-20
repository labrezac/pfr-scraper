"""CLI entry point for scraping team game logs."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from pfr_scraper.http.cookies import load_cookies_from_file
from pfr_scraper.scrapers import DEFAULT_TEAM_CODES, TeamGameLogScraper


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("season", type=int, help="Season year to scrape (e.g., 2024)")
    parser.add_argument(
        "--teams",
        metavar="TEAM",
        nargs="*",
        help="Optional subset of team codes to scrape (defaults to all active franchises)",
    )
    parser.add_argument(
        "--no-playoffs",
        action="store_true",
        help="Skip playoff game logs and only export regular season data",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if load_cookies_from_file():
        print("Loaded Cloudflare cookies from configs/cf_cookies.json")

    teams = tuple(args.teams) if args.teams else DEFAULT_TEAM_CODES
    scraper = TeamGameLogScraper(
        season=args.season,
        teams=teams,
        include_playoffs=not args.no_playoffs,
    )
    records = scraper.run()

    print(
        "Scraped {count} game log entries for season {season}.".format(
            count=len(records),
            season=args.season,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
