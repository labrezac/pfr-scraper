"""CLI entry point for scraping all active NFL players."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from pfr_scraper.http.cookies import load_cookies_from_file
from pfr_scraper.scrapers import ActivePlayersScraper


ALL_LETTERS = tuple(chr(i) for i in range(ord("A"), ord("Z") + 1))


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--letters",
        metavar="LETTER",
        nargs="*",
        help="Subset of player index letters to scrape. Defaults to all A-Z.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Seconds to wait between requests (default: 3s).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if load_cookies_from_file():
        print("Loaded Cloudflare cookies from configs/cf_cookies.json")

    letters = tuple(letter.upper() for letter in (args.letters if args.letters else ALL_LETTERS))
    invalid = [letter for letter in letters if len(letter) != 1 or not letter.isalpha()]
    if invalid:
        raise SystemExit(f"Invalid letters supplied: {', '.join(invalid)}")

    scraper = ActivePlayersScraper(letters=letters, delay_seconds=args.delay)
    records = scraper.run()

    print(f"Scraped {len(records)} active players across indices {', '.join(letters)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
