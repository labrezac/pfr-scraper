"""Concrete scrapers that pull data from Pro-Football-Reference."""

from .active_players import ActivePlayerRecord, ActivePlayersScraper
from .base import Scraper
from .team_depth_chart import TeamDepthChartRecord, TeamDepthChartScraper
from .team_game_logs import TeamGameLogRecord, TeamGameLogScraper
from .team_rosters import DEFAULT_TEAM_CODES, TeamRosterRecord, TeamRosterScraper

__all__ = [
    "Scraper",
    "ActivePlayersScraper",
    "ActivePlayerRecord",
    "TeamRosterScraper",
    "TeamRosterRecord",
    "TeamDepthChartScraper",
    "TeamDepthChartRecord",
    "TeamGameLogScraper",
    "TeamGameLogRecord",
    "DEFAULT_TEAM_CODES",
]
