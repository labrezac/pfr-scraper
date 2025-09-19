"""Session factory that wires in the header emulator."""

from __future__ import annotations

from typing import Mapping, MutableMapping, Protocol

try:
    import requests
except ImportError:  # pragma: no cover - dependency is optional until runtime
    requests = None  # type: ignore[assignment]


class HeaderProvider(Protocol):
    """Protocol describing the header emulator surface we rely on."""

    def generate(self) -> Mapping[str, str]:
        """Return a fresh set of HTTP headers."""


def build_session(
    emulator: HeaderProvider | None = None,
    *,
    base_headers: Mapping[str, str] | None = None,
) -> "requests.Session":
    """Create a `requests.Session` configured with emulator-provided headers.

    Parameters
    ----------
    emulator:
        Instance of the header emulator. Any object exposing a ``generate``
        method that returns header key/value pairs will work.
    base_headers:
        Headers that should always be present on the session. Emulator output
        overrides keys from this mapping when overlaps occur.
    """

    if requests is None:
        raise ImportError("requests must be installed to create an HTTP session")

    session = requests.Session()
    headers: MutableMapping[str, str] = session.headers.copy()

    if base_headers:
        headers.update(base_headers)

    if emulator is not None:
        headers.update(emulator.generate())

    session.headers.clear()
    session.headers.update(headers)

    return session
