"""OAuth2 for the local OpenEMR: register a client, enable it, log in with the password grant, refresh the token.

OpenEMR keeps a client that asks for user scopes disabled until an administrator enables it, and offers no API for that.
The container is ours and local, so the one enabling step is a SQL update run inside the database container. Secrets
(client secret, tokens, admin password) live only under the work folder (out/openemr/, git-ignored) and are never logged.
"""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

import httpx

from krisnai.integrations.clearinghouse.client import check_endpoint
from krisnai.integrations.openemr.docker import HTTPS_URL, PROJECT

CLIENT_NAME = "krisnai-local"
REDIRECT = f"{HTTPS_URL}/krisnai/callback"
SCOPES = [
    "openid", "offline_access", "api:oemr", "api:fhir",
    "user/Patient.read", "user/Patient.write", "user/Practitioner.read", "user/Practitioner.write",
    "user/Organization.read", "user/Organization.write", "user/Appointment.read", "user/Encounter.read",
    "user/DocumentReference.read", "user/Binary.read",
    "user/patient.read", "user/patient.write", "user/appointment.read", "user/appointment.write",
    "user/encounter.read", "user/encounter.write", "user/document.read", "user/document.write",
    "user/soap_note.read", "user/soap_note.write", "user/practitioner.read", "user/facility.read",
    "user/facility.write", "user/Coverage.read", "user/insurance.read", "user/insurance.write",
    "user/insurance_company.read", "user/insurance_company.write", "user/message.write",
]  # fmt: skip
REFRESH_MARGIN = 60  # seconds before expiry at which a new token is fetched


class AuthError(Exception):
    """Registration or login failed. The message never contains a secret."""


def _docker_sql(statement: str) -> None:
    """Run one statement as root inside the database container (the root password is read inside the container)."""
    res = subprocess.run(
        ["docker", "exec", f"{PROJECT}-db-1", "sh", "-c", 'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" openemr -e "$0"',
         statement],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    if res.returncode != 0:
        raise AuthError("could not enable the API client in the OpenEMR database (is the container running?)")


class OpenEmrAuth:
    def __init__(self, work: Path, base: str = HTTPS_URL, http: httpx.Client | None = None,
                 run_sql: Callable[[str], None] = _docker_sql, clock: Callable[[], float] = time.time):  # fmt: skip
        check_endpoint(base)
        self.work, self.base, self.run_sql, self.clock = work, base.rstrip("/"), run_sql, clock
        # local container with a self-signed certificate: verification is off, and check_endpoint keeps this local-only
        self._http = http or httpx.Client(verify=False, timeout=30)  # noqa: S501
        self._token: str | None = None
        self._refresh: str | None = None
        self._expires = 0.0

    # ------------------------------------------------------------------------------------------ client
    @property
    def _client_file(self) -> Path:
        return self.work / "client.json"

    def ensure_client(self) -> dict:
        if self._client_file.exists():
            have = json.loads(self._client_file.read_text(encoding="utf-8"))
            if set(have["scope"].split()) >= set(SCOPES):
                return have
            # scopes were added since this client was registered: register a new one (the old one stays unused)
        body = {
            "application_type": "private", "redirect_uris": [REDIRECT], "client_name": CLIENT_NAME,
            "token_endpoint_auth_method": "client_secret_post", "contacts": ["local@example.test"],
            "scope": " ".join(SCOPES),
        }  # fmt: skip
        r = self._http.post(f"{self.base}/oauth2/default/registration", json=body)
        if r.status_code >= 400:
            raise AuthError(f"client registration failed (HTTP {r.status_code}): {r.json().get('error', '')}")
        d = r.json()
        self.run_sql(f"update oauth_clients set is_enabled=1 where client_id='{d['client_id']}'")
        client = {"client_id": d["client_id"], "client_secret": d["client_secret"], "scope": " ".join(SCOPES)}
        self.work.mkdir(parents=True, exist_ok=True)
        self._client_file.write_text(json.dumps(client), encoding="utf-8")
        return client

    # ------------------------------------------------------------------------------------------ tokens
    def _fetch(self, form: dict) -> None:
        client = self.ensure_client()
        r = self._http.post(f"{self.base}/oauth2/default/token",
                            data={**form, "client_id": client["client_id"], "client_secret": client["client_secret"]})  # fmt: skip
        if r.status_code >= 400:
            raise AuthError(f"login failed (HTTP {r.status_code}): {r.json().get('error', '')}")
        d = r.json()
        self._token = d["access_token"]
        self._refresh = d.get("refresh_token") or self._refresh
        self._expires = self.clock() + float(d.get("expires_in", 3600))

    def _login(self) -> None:
        password = (self.work / "admin_password.txt").read_text(encoding="utf-8").strip()
        self._fetch({"grant_type": "password", "user_role": "users", "username": "admin", "password": password,
                     "scope": self.ensure_client()["scope"]})  # fmt: skip

    def token(self) -> str:
        """A valid access token: cached, refreshed shortly before expiry, or a new login if refreshing fails."""
        if self._token and self.clock() < self._expires - REFRESH_MARGIN:
            return self._token
        if self._refresh:
            try:
                self._fetch({"grant_type": "refresh_token", "refresh_token": self._refresh})
                return self._token  # type: ignore[return-value]
            except AuthError:
                self._refresh = None
        self._login()
        return self._token  # type: ignore[return-value]
