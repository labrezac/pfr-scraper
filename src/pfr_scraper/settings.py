"""Project-wide configuration helpers."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class DataPaths:
    """Collection of local directories used by the scraper pipelines."""

    root: Path = Path("data")

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def processed(self) -> Path:
        return self.root / "processed"


@dataclass(slots=True)
class Settings:
    """Runtime settings for scraper jobs."""

    user_agent_seed: str = "pfr-scraper"
    request_timeout: float = 10.0
    data_paths: DataPaths = DataPaths()


settings = Settings()
