"""CLI entry point for scraping all active NFL players."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from pfr_scraper.http.cookies import load_cookies_from_file
from pfr_scraper.scrapers import ActivePlayersScraper


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "letter",
        metavar="LETTER",
        help=(
            "Single player index letter to scrape (A-Z). Run this command multiple "
            "times to build the full active roster dataset."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if load_cookies_from_file():
        print("Loaded Cloudflare cookies from configs/cf_cookies.json")

    letter = args.letter.upper()
    if len(letter) != 1 or not letter.isalpha():
        raise SystemExit("letter must be a single alphabetical character (A-Z)")

    scraper = ActivePlayersScraper(letters=(letter,))
    records = scraper.run()

    print(f"Scraped {len(records)} active players for index '{letter}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
