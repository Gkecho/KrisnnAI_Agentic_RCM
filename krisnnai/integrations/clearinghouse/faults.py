"""Deterministic fault injection for the clearinghouse bots (tests and the Stage 1 failure drill; never a real client).

`FaultyClient` wraps any client with check_eligibility / claim_status / submit_claim and misbehaves on chosen calls.
Calls are numbered 1, 2, 3 ... across all three methods. There is no randomness: the same schedule gives the same run.

    FaultyClient(inner, {2: "timeout", 3: "http_5xx"}, outage_after=6)

Faults
    timeout              ReadTimeout before the request is sent
    timeout_after_send   the inner client processes the request, then the reply is lost (ReadTimeout)
    connection_error     ConnectError, the request never left
    http_5xx / http_401 / http_400   the matching HTTP status error
    garbage              a body that is not X12
    truncated            the real reply cut in half (a broken envelope)
    wrong_subject        the previous reply is delivered again, for a different request
    outage_after=n       every call after the n-th fails with ConnectError
"""

from __future__ import annotations

import httpx

FAULTS = {
    "timeout", "timeout_after_send", "connection_error", "http_5xx", "http_401", "http_400", "garbage", "truncated",
    "wrong_subject",
}  # fmt: skip

_REQUEST = httpx.Request("POST", "http://testserver/fault")


def _status(code: int) -> httpx.HTTPStatusError:
    return httpx.HTTPStatusError(f"HTTP {code}", request=_REQUEST, response=httpx.Response(code, request=_REQUEST))


class FaultyClient:
    def __init__(self, inner, schedule: dict[int, str] | None = None, outage_after: int | None = None):  # noqa: ANN001
        unknown = set((schedule or {}).values()) - FAULTS
        if unknown:
            raise ValueError(f"unknown fault(s): {', '.join(sorted(unknown))}")
        self.inner, self.schedule, self.outage_after = inner, dict(schedule or {}), outage_after
        self.calls = 0
        self.delivered: list = []  # replies handed to the caller, oldest first
        self.log: list[tuple[int, str, str]] = []  # (call number, method, fault or "ok")

    def _run(self, method: str, request: str):  # noqa: ANN202
        self.calls += 1
        n = self.calls
        fault = "outage" if self.outage_after is not None and n > self.outage_after else self.schedule.get(n, "ok")
        self.log.append((n, method, fault))
        fn = getattr(self.inner, method)
        if fault in ("outage", "connection_error"):
            raise httpx.ConnectError("injected: connection refused", request=_REQUEST)
        if fault == "timeout":
            raise httpx.ReadTimeout("injected: timeout", request=_REQUEST)
        if fault == "http_5xx":
            raise _status(503)
        if fault == "http_401":
            raise _status(401)
        if fault == "http_400":
            raise _status(400)
        if fault == "wrong_subject":
            if not self.delivered:
                raise ValueError("wrong_subject needs an earlier reply to repeat; schedule it after the first call")
            return self.delivered[-1]
        reply = fn(request)
        if fault == "timeout_after_send":
            raise httpx.ReadTimeout("injected: reply lost", request=_REQUEST)
        if fault == "garbage":
            return "<html>502 Bad Gateway</html>"
        if fault == "truncated":
            if isinstance(reply, dict):
                return {"results": []}
            return reply[: len(reply) // 2]
        self.delivered.append(reply)
        return reply

    def check_eligibility(self, x12_270: str) -> str:
        return self._run("check_eligibility", x12_270)

    def claim_status(self, x12_276: str) -> str:
        return self._run("claim_status", x12_276)

    def submit_claim(self, x12_837: str) -> dict:
        return self._run("submit_claim", x12_837)
