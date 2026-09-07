"""Minimal HTTP client for the League of Legends client's local API (LCU).

The client exposes its API on https://127.0.0.1:<port> behind a self-signed
certificate: TLS verification is disabled on purpose.
"""

import json
from typing import Any

import requests
import urllib3

from .i18n import t
from .lockfile import Credentials

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LcuError(RuntimeError):
    """HTTP error returned by the LCU. Carries the whole response."""

    def __init__(self, message: str, response: requests.Response) -> None:
        super().__init__(message)
        self.response = response


def format_response(response: requests.Response) -> str:
    """Render an HTTP response in full: status, headers, body.

    The body is never truncated nor swallowed: it is the only way to adjust the
    payloads sent to endpoints that have not been verified yet.
    """
    lines = [
        t("http.header"),
        f"{response.request.method} {response.request.url}",
        f"HTTP {response.status_code} {response.reason}",
    ]

    request_body = response.request.body
    if request_body:
        if isinstance(request_body, bytes):
            request_body = request_body.decode("utf-8", errors="replace")
        lines.append(t("http.request_body"))
        lines.append(request_body)

    lines.append(t("http.response_headers"))
    for name, value in response.headers.items():
        lines.append(f"  {name}: {value}")

    lines.append(t("http.response_body"))
    text = response.text
    if not text:
        lines.append(t("http.empty"))
    else:
        try:
            lines.append(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except ValueError:
            lines.append(text)

    lines.append(t("http.footer"))
    return "\n".join(lines)


class LcuClient:
    """Authenticated HTTP session against the LCU."""

    def __init__(self, credentials: Credentials, timeout: float = 10.0) -> None:
        self.credentials = credentials
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = credentials.auth
        self.session.verify = False
        self.session.headers.update({"Accept": "application/json"})

    @property
    def base_url(self) -> str:
        return self.credentials.base_url

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        """Send a request. Does not raise on an HTTP error status."""
        url = f"{self.base_url}{path}"
        kwargs.setdefault("timeout", self.timeout)
        return self.session.request(method, url, **kwargs)

    def request_checked(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        """Like `request`, but raises `LcuError` with the full response on 4xx/5xx."""
        response = self.request(method, path, **kwargs)
        if response.status_code >= 400:
            summary = t("http.failed", method=method, path=path, status=response.status_code)
            raise LcuError(f"{summary}\n{format_response(response)}", response)
        return response

    def get_json(self, path: str, **kwargs: Any) -> Any:
        return self.request_checked("GET", path, **kwargs).json()

    def post_json(self, path: str, payload: Any, **kwargs: Any) -> requests.Response:
        return self.request_checked("POST", path, json=payload, **kwargs)

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "LcuClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def check_connection(client: LcuClient) -> dict[str, Any]:
    """Check that the LCU answers. Returns GET /lol-summoner/v1/current-summoner."""
    return client.get_json("/lol-summoner/v1/current-summoner")
