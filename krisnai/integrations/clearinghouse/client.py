"""Client for a clearinghouse that takes X12 over HTTPS. Points at the local mock now; a real sandbox later by config.

Safety: only localhost URLs are accepted unless KRISNAI_ALLOW_REAL_ENDPOINTS=1 is set in the environment. The token is
never logged and never read from a file in the repo.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

import httpx

ALLOW_ENV = "KRISNAI_ALLOW_REAL_ENDPOINTS"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "testserver"}


class EndpointRefused(Exception):
    """The URL is not local and real endpoints have not been enabled."""


def check_endpoint(url: str) -> None:
    host = urlparse(url).hostname or ""
    if host in LOCAL_HOSTS or host.endswith(".localhost") or host.endswith(".test"):
        return
    if os.environ.get(ALLOW_ENV) == "1":
        return
    raise EndpointRefused(
        f"{host or url} is not a local endpoint; set {ALLOW_ENV}=1 to allow a real sandbox (never a production payer)"
    )


class ClearinghouseClient:
    def __init__(self, base_url: str, token: str, http: httpx.Client | None = None, timeout: float = 30):
        """`http` lets a test pass an in-process client (FastAPI's TestClient); the URL check still applies."""
        check_endpoint(base_url)
        self.base_url = base_url.rstrip("/")
        self._http = http or httpx.Client(base_url=self.base_url, timeout=timeout)
        self._http.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "text/plain"})

    def close(self) -> None:
        self._http.close()

    def health(self) -> dict:
        return self._http.get("/v1/health").raise_for_status().json()

    def check_eligibility(self, x12_270: str) -> str:
        return self._http.post("/v1/eligibility", content=x12_270).raise_for_status().text

    def claim_status(self, x12_276: str) -> str:
        return self._http.post("/v1/claim-status", content=x12_276).raise_for_status().text

    def submit_claim(self, x12_837: str) -> dict:
        return self._http.post("/v1/claims", content=x12_837).raise_for_status().json()
