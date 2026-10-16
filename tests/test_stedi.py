"""The Stedi adapter against recorded-shape responses (no network). A live smoke test runs only with a test key set."""

from __future__ import annotations

import json
import os
from datetime import date

import httpx
import pytest

from krisnai.integrations.clearinghouse.client import ALLOW_ENV, EndpointRefused
from krisnai.integrations.clearinghouse.stedi import (
    BASE,
    CLAIM_STATUS,
    CLAIMS,
    ELIGIBILITY,
    PRODUCTION_ENV,
    SUBMIT_ENV,
    ProductionKeyRefused,
    StediClient,
    StediError,
)
from krisnai.integrations.clearinghouse.x12_out import write_270

KEY = "test_key_not_a_real_secret"


def client_with(handler, monkeypatch, **kw):
    monkeypatch.setenv("STEDI_API_KEY", KEY)
    monkeypatch.setenv(ALLOW_ENV, "1")
    return StediClient(http=httpx.Client(transport=httpx.MockTransport(handler)), **kw)


def seen(requests):
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path.endswith("raw-x12") and "eligibility" in path:
            return httpx.Response(200, json={"x12": "ISA...271", "meta": {"applicationMode": "test"}, "status": "SUCCESS"})
        if path.endswith("raw-x12") and "claimstatus" in path:
            return httpx.Response(200, json={"x12": "ISA...277", "claims": []})
        if path.endswith("raw-x12-submission"):
            return httpx.Response(200, json={"status": "SUCCESS", "x12": "ISA...277CA", "errors": [],
                                             "meta": {"applicationMode": "test"}})  # fmt: skip
        return httpx.Response(404, json={"message": "no such path"})

    return handler


def test_the_three_calls_use_stedis_raw_x12_paths_and_return_the_x12(monkeypatch):
    reqs: list[httpx.Request] = []
    c = client_with(seen(reqs), monkeypatch)
    assert c.check_eligibility("270text") == "ISA...271"
    assert c.claim_status("276text") == "ISA...277"
    assert [r.url.path for r in reqs] == [
        "/2024-04-01" + ELIGIBILITY, "/2024-04-01" + CLAIM_STATUS,
    ]
    assert str(reqs[0].url).startswith(BASE)
    assert json.loads(reqs[0].content) == {"x12": "270text"}
    assert reqs[0].headers["authorization"] == KEY  # the bare key, as the reference shows


def test_key_style_can_be_switched_to_the_older_prefix(monkeypatch):
    reqs: list[httpx.Request] = []
    c = client_with(seen(reqs), monkeypatch, auth_style="key")
    c.check_eligibility("270")
    assert reqs[0].headers["authorization"] == f"Key {KEY}"


def test_submission_is_off_until_deliberately_enabled_and_confirmed_as_a_test_key(monkeypatch):
    reqs: list[httpx.Request] = []
    c = client_with(seen(reqs), monkeypatch)
    monkeypatch.delenv(SUBMIT_ENV, raising=False)
    with pytest.raises(StediError, match="off"):
        c.submit_claim("CLM*C1*100*")
    monkeypatch.setenv(SUBMIT_ENV, "1")
    with pytest.raises(StediError, match="test-mode"):
        c.submit_claim("CLM*C1*100*")
    assert not reqs
    res = c.submit_claim("ISA~CLM*C1*100***11:B:7~CLM*C2*50***11:B:7~", confirm_test_key=True)
    assert [(r["claim"], r["ok"]) for r in res["results"]] == [("C1", True), ("C2", True)]
    assert res["277CA"] == "ISA...277CA"
    assert reqs[0].headers["idempotency-key"]  # a retry within 24 h must not create a duplicate claim


def test_a_rejected_submission_reports_the_reason(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"status": "ERROR", "x12": "", "errors": [{"description": "bad NPI"}],
                                         "meta": {"applicationMode": "test"}})  # fmt: skip

    c = client_with(handler, monkeypatch)
    monkeypatch.setenv(SUBMIT_ENV, "1")
    res = c.submit_claim("CLM*C1*100*", confirm_test_key=True)
    assert res["results"][0]["ok"] is False and "bad NPI" in res["results"][0]["reason"]


def test_a_production_mode_response_stops_the_client(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"x12": "ISA", "meta": {"applicationMode": "production"}})

    c = client_with(handler, monkeypatch)
    monkeypatch.delenv(PRODUCTION_ENV, raising=False)
    # a test_ key is trusted even though Stedi labels its responses "production"
    assert c.check_eligibility("270") == "ISA"
    c._test_key = False
    with pytest.raises(ProductionKeyRefused):
        c.check_eligibility("270")


def test_http_errors_become_a_clear_error_without_the_key(monkeypatch):
    def handler(request):
        return httpx.Response(403, json={"message": "Access denied", "code": "AccessDenied"})

    c = client_with(handler, monkeypatch)
    with pytest.raises(StediError) as e:
        c.check_eligibility("270")
    assert "403" in str(e.value) and KEY not in str(e.value)


def test_no_key_or_a_remote_url_without_the_flag_is_refused(monkeypatch):
    monkeypatch.delenv("STEDI_API_KEY", raising=False)
    monkeypatch.setenv(ALLOW_ENV, "1")
    with pytest.raises(SystemExit):
        StediClient()
    monkeypatch.setenv("STEDI_API_KEY", KEY)
    monkeypatch.delenv(ALLOW_ENV, raising=False)
    with pytest.raises(EndpointRefused):
        StediClient()


@pytest.mark.skipif(not (os.environ.get("STEDI_API_KEY") and os.environ.get(ALLOW_ENV) == "1"),
                    reason="live smoke test: needs STEDI_API_KEY (a TEST key) and KRISNAI_ALLOW_REAL_ENDPOINTS=1")  # fmt: skip
def test_live_eligibility_returns_an_x12_envelope():
    c = StediClient()
    # Stedi's documented mock subscriber (Aetna, medical, service type 30); other values return an error in test mode
    x12 = write_270("60054", "AETNA", "AETNA9wcSu", "Doe", "John", "19800101", date.today(), "KRISNAILIVE", 1,
                    date.today())  # fmt: skip
    text = c.check_eligibility(x12)
    assert text.startswith("ISA") and c.last_mode in (None, "test")
