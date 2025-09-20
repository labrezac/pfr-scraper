"""CLI entry point for scraping team depth charts."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from pfr_scraper.scrapers import DEFAULT_TEAM_CODES, TeamDepthChartScraper


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("season", type=int, help="Season year to scrape (e.g., 2024)")
    parser.add_argument(
        "--teams",
        metavar="TEAM",
        nargs="*",
        help="Optional subset of team codes to scrape (defaults to all active franchises)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    teams = tuple(args.teams) if args.teams else DEFAULT_TEAM_CODES
    scraper = TeamDepthChartScraper(season=args.season, teams=teams)
    records = scraper.run()

    print(f"Scraped {len(records)} depth chart slots for season {args.season}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
