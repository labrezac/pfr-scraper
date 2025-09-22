# pfr-scraper

Playground for webscraping Pro-Football-Reference.

## HTTP configuration

The project honours optional overrides for Cloudflare/session headers via environment variables:

- `PFR_HTTP_HEADER_<NAME>` injects a default header (use `__` to represent hyphens, for example `PFR_HTTP_HEADER_Sec__Ch__Ua`).
- `PFR_HTTP_COOKIE_<NAME>` injects a cookie (e.g. export `PFR_HTTP_COOKIE_cf_clearance` with the value copied from a browser session).

When present, these values are applied to every `requests.Session` the scrapers create, allowing you to pass along Cloudflare clearance tokens or other authentication hints without editing code.

## Rate-limited scraping

To minimise Cloudflare challenges the active-player CLI scrapes a single index letter per run:

```
python scripts/run_active_players.py --letters A B --delay 3
```

Omit `--letters` to process all A-Z in one run; the delay is applied between each request to stay under the radar.

### Browser fallback

If requests-based fetching still returns 403s, point the scraper at a real Chrome profile by exporting:

```
export PFR_PLAYWRIGHT_PROFILE_DIR="/Users/you/Library/Application Support/Google/Chrome/Profile 5"
```

The fetcher will transparently fall back to Playwright, reusing the cookies stored in that profile. You can combine this with `fetch_cf_cookies.py --extend` to keep the clearance tokens in `configs/cf_cookies.json`.

### Harvesting Cloudflare cookies

If the site responds with 403 challenges, capture fresh clearance cookies via Playwright:

```
python scripts/fetch_cf_cookies.py
```

The command writes `configs/cf_cookies.json`. All CLI entry points load this file automatically, merging the cookies into outbound sessions.

## Project layout

```
├── configs/              # Configuration files shared across scrapers and pipelines
├── data/                 # Local data lake (raw + processed datasets)
│   ├── processed/
│   └── raw/
├── logs/                 # Runtime logs emitted by scraper jobs
├── notebooks/            # Exploratory analysis and spike notebooks
├── scripts/              # Command-line entry points for running scrapers/pipelines
├── src/pfr_scraper/
│   ├── http/             # HTTP utilities that wrap the header emulator
│   ├── pipelines/        # Data processing pipelines fed by scraper outputs
│   └── scrapers/         # Concrete scraper implementations
└── tests/                # Automated tests
```
