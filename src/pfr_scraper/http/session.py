"""Session factory that wires in the header emulator."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Protocol, TYPE_CHECKING

try:
    import requests
except ImportError:  # pragma: no cover - dependency is optional until runtime
    requests = None  # type: ignore[assignment]

from pfr_scraper.settings import settings

try:  # pragma: no cover - optional dependency during import
    from header_emulator import HeaderEmulator
    from header_emulator.session import RETRYABLE_STATUS_CODES
except ImportError:  # pragma: no cover - degrade gracefully until installed
    HeaderEmulator = None  # type: ignore[assignment]
    RETRYABLE_STATUS_CODES = {403, 407, 408, 425, 429, 500, 502, 503, 504}

if TYPE_CHECKING:  # pragma: no cover - typing only
    from header_emulator.types import EmulatedRequest, ProxyConfig


class HeaderProvider(Protocol):
    """Protocol describing the minimal header emulator surface we rely on."""

    def next_request(self) -> "EmulatedRequest":  # pragma: no cover - protocol only
        """Return an emulated request payload with headers/cookies."""


_DEFAULT_EMULATOR: "HeaderEmulator | None" = None


def build_session(
    emulator: HeaderProvider | None = None,
    *,
    base_headers: Mapping[str, str] | None = None,
) -> "requests.Session":
    """Create a `requests.Session` configured with emulator-driven headers.

    Parameters
    ----------
    emulator:
        Instance of the header emulator. Objects exposing a ``next_request``
        method (such as :class:`header_emulator.HeaderEmulator`) are supported.
        When omitted we lazily construct a shared default emulator instance.
    base_headers:
        Headers that should always be present on the session. Per-request
        emulator output overrides keys from this mapping when overlaps occur.
    """

    if requests is None:
        raise ImportError("requests must be installed to create an HTTP session")

    resolved_emulator = emulator or _get_default_emulator()

    session = requests.Session()
    headers: MutableMapping[str, str] = session.headers.copy()

    if settings.http.base_headers:
        headers.update(settings.http.base_headers)

    if settings.user_agent_seed and "User-Agent" not in headers:
        headers["User-Agent"] = settings.user_agent_seed

    if base_headers:
        headers.update(base_headers)

    session.headers.clear()
    session.headers.update(headers)

    if settings.http.cookies:
        session.cookies.update(settings.http.cookies)

    _attach_request_pipeline(session, resolved_emulator)

    return session


def _get_default_emulator() -> HeaderProvider:
    if HeaderEmulator is None:
        raise ImportError(
            "header-emulator must be installed or on PYTHONPATH to build a session",
        )

    global _DEFAULT_EMULATOR
    if _DEFAULT_EMULATOR is None:
        _DEFAULT_EMULATOR = HeaderEmulator()
    return _DEFAULT_EMULATOR


def _attach_request_pipeline(session: "requests.Session", emulator: HeaderProvider) -> None:
    original_request = session.request

    def request(method: str, url: str, **kwargs: Any) -> Any:
        emulated = emulator.next_request()

        headers = session.headers.copy()
        headers.update(emulated.headers)

        extra_headers = kwargs.pop("headers", None)
        if extra_headers:
            headers.update(extra_headers)
        kwargs["headers"] = headers

        cookies = dict(emulated.cookies)
        extra_cookies = kwargs.pop("cookies", None)
        if extra_cookies:
            cookies.update(extra_cookies)
        if cookies:
            kwargs["cookies"] = cookies

        if emulated.proxy is not None and kwargs.get("proxies") is None:
            kwargs["proxies"] = _proxy_mapping(emulated.proxy)

        kwargs.setdefault("timeout", settings.request_timeout)

        try:
            response = original_request(method, url, **kwargs)
        except requests.RequestException:
            _record_failure(emulator, emulated)
            _mark_proxy(emulator, emulated.proxy, success=False)
            raise

        if _should_flag_failure(response):
            _record_failure(emulator, emulated)
            _mark_proxy(emulator, emulated.proxy, success=False)
        else:
            _record_success(emulator, emulated)
            _mark_proxy(emulator, emulated.proxy, success=True)

        return response

    session.request = request  # type: ignore[assignment]


def _should_flag_failure(response: Any) -> bool:
    status = getattr(response, "status_code", None)
    if status is None:
        return False
    if status in RETRYABLE_STATUS_CODES:
        return True
    return 500 <= status


def _record_success(emulator: HeaderProvider, emulated: "EmulatedRequest") -> None:
    rotator = getattr(emulator, "rotator", None)
    profile_id = getattr(emulated, "profile_id", None)
    if rotator is not None and profile_id:
        rotator.record_success(profile_id)


def _record_failure(emulator: HeaderProvider, emulated: "EmulatedRequest") -> None:
    rotator = getattr(emulator, "rotator", None)
    profile_id = getattr(emulated, "profile_id", None)
    if rotator is not None and profile_id:
        rotator.record_failure(profile_id)


def _mark_proxy(emulator: HeaderProvider, proxy: "ProxyConfig | None", *, success: bool) -> None:
    if proxy is None:
        return

    builder = getattr(emulator, "builder", None)
    manager = getattr(builder, "proxy_manager", None)
    if manager is None:
        return

    if success:
        manager.mark_success(proxy)
    else:
        manager.mark_failure(proxy)


def _proxy_mapping(proxy: "ProxyConfig") -> dict[str, str]:
    url = proxy.url
    return {"http": url, "https": url}
