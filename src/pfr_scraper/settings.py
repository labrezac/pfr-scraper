"""Project-wide configuration helpers."""

from dataclasses import dataclass, field
from pathlib import Path
import os


def _env_mapping(prefix: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    offset = len(prefix)
    for key, value in os.environ.items():
        if key.startswith(prefix):
            normalized = key[offset:]
            normalized = normalized.replace("__", "-")
            mapping[normalized] = value
    return mapping


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
class HttpSettings:
    """Optional overrides for HTTP headers and cookies."""

    base_headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    playwright_profile_dir: Path | None = None

    @classmethod
    def from_env(cls) -> "HttpSettings":
        headers = _env_mapping("PFR_HTTP_HEADER_")
        cookies = _env_mapping("PFR_HTTP_COOKIE_")
        profile_env = os.environ.get("PFR_PLAYWRIGHT_PROFILE_DIR")
        profile_dir = Path(profile_env).expanduser() if profile_env else None
        return cls(
            base_headers=headers,
            cookies=cookies,
            playwright_profile_dir=profile_dir,
        )


@dataclass(slots=True)
class Settings:
    """Runtime settings for scraper jobs."""

    user_agent_seed: str = "pfr-scraper"
    request_timeout: float = 10.0
    data_paths: DataPaths = field(default_factory=DataPaths)
    http: "HttpSettings" = field(default_factory=lambda: HttpSettings.from_env())


settings = Settings()
