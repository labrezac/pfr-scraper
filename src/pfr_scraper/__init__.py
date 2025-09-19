"""Top-level package for the pfr_scraper project."""

from importlib import metadata

try:
    __version__ = metadata.version("pfr-scraper")
except metadata.PackageNotFoundError:  # pragma: no cover - fallback for local dev
    __version__ = "0.0.0"

__all__ = ["__version__"]
