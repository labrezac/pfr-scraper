"""CLI entry point for scraping all active NFL players."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from pfr_scraper.scrapers import ActivePlayersScraper


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--letters",
        metavar="LETTER",
        nargs="*",
        help="Optional subset of player index letters to scrape (defaults to A-Z)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    scraper = ActivePlayersScraper(letters=args.letters if args.letters else None)
    records = scraper.run()

    print(f"Scraped {len(records)} active players.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
