# Scripts

Entry points for running scrapers and pipelines from the command line will live here.

## Available scripts

- `python scripts/run_active_players.py [--letters A B ...]`: fetch active players (defaults to all A-Z indexes) and store the compiled CSV under `data/processed/active_players.csv`.
- `python scripts/run_team_rosters.py SEASON [--teams sfo nyg ...]`: pull roster tables for the given season, persisting results to `data/processed/team_rosters_SEASON.csv` and HTML snapshots under `data/raw/team_rosters/SEASON/`.
- `python scripts/run_team_depth_chart.py SEASON [--teams sfo nyg ...]`: capture depth chart slots for the season, writing `data/processed/team_depth_chart_SEASON.csv` and raw pages to `data/raw/team_depth_charts/SEASON/`.
