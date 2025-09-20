# Scripts

Entry points for running scrapers and pipelines from the command line will live here.

## Available scripts

- `python scripts/run_active_players.py LETTER`: fetch active players for a single index letter (A-Z) and append to `data/processed/active_players.csv`. Run repeatedly for additional letters.
- `python scripts/run_team_rosters.py SEASON [--teams sfo nyg ...]`: pull roster tables for the given season, persisting results to `data/processed/team_rosters_SEASON.csv` and HTML snapshots under `data/raw/team_rosters/SEASON/`.
- `python scripts/run_team_depth_chart.py SEASON [--teams sfo nyg ...]`: capture depth chart slots for the season, writing `data/processed/team_depth_chart_SEASON.csv` and raw pages to `data/raw/team_depth_charts/SEASON/`.
- `python scripts/run_team_game_logs.py SEASON [--teams sfo nyg ...] [--no-playoffs]`: export per-game logs (regular season by default, playoffs optional) with results saved to `data/processed/team_game_logs_SEASON.csv` and snapshots under `data/raw/team_game_logs/SEASON/`.
- `python scripts/fetch_cf_cookies.py`: open a headless Chromium session via Playwright, solve the Cloudflare challenge, and dump the resulting cookies to `configs/cf_cookies.json` for reuse by other scrapers.
