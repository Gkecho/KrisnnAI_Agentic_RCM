"""Local OpenEMR: generated passwords, client registration + enabling, token cache and refresh, bearer provider on the FHIR client."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from krisnnai.integrations.clearinghouse.client import EndpointRefused
from krisnnai.integrations.fhir.client import FhirClient
from krisnnai.integrations.openemr import docker as oedocker
from krisnnai.integrations.openemr.auth import AuthError, OpenEmrAuth

SECRET = "client-secret-xyz"
ADMIN = "AdminPw-123!A1"


class FakeOpenEmr:
    """Registration + token endpoints. Counts calls; can reject refresh tokens."""

    def __init__(self, refuse_refresh: bool = False):
        self.registrations = self.logins = self.refreshes = 0
        self.refuse_refresh = refuse_refresh
        self.seen_passwords: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/registration"):
            self.registrations += 1
            return httpx.Response(200, json={"client_id": "cid-1", "client_secret": SECRET})
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        assert form["client_id"] == "cid-1" and form["client_secret"] == SECRET
        if form["grant_type"] == "password":
            self.logins += 1
            self.seen_passwords.append(form["password"])
            return httpx.Response(200, json={"access_token": f"tok-login-{self.logins}", "refresh_token": "r1", "expires_in": 3600})
        self.refreshes += 1
        if self.refuse_refresh:
            return httpx.Response(400, json={"error": "invalid_grant"})
        return httpx.Response(200, json={"access_token": f"tok-refresh-{self.refreshes}", "expires_in": 3600})


@pytest.fixture()
def work(tmp_path) -> Path:
    (tmp_path / "admin_password.txt").write_text(ADMIN, encoding="utf-8")
    return tmp_path


def make_auth(work, server, clock, sql=None):
    http = httpx.Client(transport=httpx.MockTransport(server))
    return OpenEmrAuth(work, http=http, run_sql=(sql if sql is not None else (lambda s: None)), clock=clock)


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_the_client_is_registered_enabled_once_and_remembered(work):
    server, sql, clock = FakeOpenEmr(), [], Clock()
    auth = make_auth(work, server, clock, sql.append)
    auth.token()
    assert server.registrations == 1 and len(sql) == 1 and "is_enabled=1" in sql[0] and "cid-1" in sql[0]
    again = make_auth(work, server, clock, sql.append)  # a new process reads client.json
    again.token()
    assert server.registrations == 1 and len(sql) == 1
    assert json.loads((work / "client.json").read_text())["client_id"] == "cid-1"


def test_a_token_is_cached_then_refreshed_before_it_expires(work):
    server, clock = FakeOpenEmr(), Clock()
    auth = make_auth(work, server, clock)
    assert auth.token() == "tok-login-1" and auth.token() == "tok-login-1" and server.logins == 1
    clock.now += 3600 - 30  # inside the refresh margin
    assert auth.token() == "tok-refresh-1" and server.refreshes == 1 and server.logins == 1


def test_a_refused_refresh_falls_back_to_a_new_login(work):
    server, clock = FakeOpenEmr(refuse_refresh=True), Clock()
    auth = make_auth(work, server, clock)
    auth.token()
    clock.now += 4000
    assert auth.token() == "tok-login-2" and server.logins == 2


def test_the_admin_password_comes_from_the_work_folder_and_is_not_in_errors(work):
    server, clock = FakeOpenEmr(), Clock()
    make_auth(work, server, clock).token()
    assert server.seen_passwords == [ADMIN]

    def deny(request):
        return httpx.Response(400, json={"error": "invalid_grant"})

    bad = OpenEmrAuth(work, http=httpx.Client(transport=httpx.MockTransport(deny)), run_sql=lambda s: None)
    (work / "client.json").write_text(json.dumps({"client_id": "cid-1", "client_secret": SECRET, "scope": "openid"}))
    with pytest.raises(AuthError) as err:
        bad.token()
    assert ADMIN not in str(err.value) and SECRET not in str(err.value)


def test_a_non_local_openemr_is_refused(work):
    with pytest.raises(EndpointRefused):
        OpenEmrAuth(work, base="https://emr.example.com")


def test_the_fhir_client_asks_the_provider_for_a_token_on_every_request():
    seen: list[str] = []

    def handler(request):
        seen.append(request.headers.get("Authorization", ""))
        return httpx.Response(200, json={"resourceType": "CapabilityStatement"})

    tokens = iter(["t1", "t2"])
    client = FhirClient("https://localhost:9300/apis/default/fhir", http=httpx.Client(transport=httpx.MockTransport(handler),
                        base_url="https://localhost:9300/apis/default/fhir"), token_provider=lambda: next(tokens))  # fmt: skip
    client.capability()
    client.capability()
    assert seen == ["Bearer t1", "Bearer t2"]


def test_generated_passwords_are_created_once_and_never_in_the_compose_file(tmp_path):
    first = oedocker.passwords(tmp_path / "w")
    assert first == oedocker.passwords(tmp_path / "w") and first["db"] != first["admin"] and len(first["admin"]) >= 20
    compose = oedocker.COMPOSE.read_text(encoding="utf-8")
    assert first["db"] not in compose and "${KRISNNAI_OPENEMR_ADMIN_PASSWORD" in compose
    assert "127.0.0.1:8300" in compose and "127.0.0.1:9300" in compose  # local only
