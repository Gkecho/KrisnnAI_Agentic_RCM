"""Start and stop a local OpenEMR (OpenEMR + MariaDB) with Docker Compose.

The database and admin passwords are generated for this run and written under the output folder; they are throwaway
credentials for containers that only listen on 127.0.0.1. First start pulls about 1-2 GB of images and OpenEMR needs a
few minutes to install itself.
"""

from __future__ import annotations

import os
import secrets
import shutil
import string
import subprocess
import time
from pathlib import Path

import httpx

COMPOSE = Path(__file__).with_name("docker-compose.openemr.yml")
HTTP_URL = "http://localhost:8300"
HTTPS_URL = "https://localhost:9300"
FHIR_PATH = "/apis/default/fhir"
PROJECT = "krisnnai-openemr"


def _secret(n: int = 22) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def _read_or_create(path: Path, make) -> str:  # noqa: ANN001
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(make(), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


def passwords(work: Path) -> dict[str, str]:
    """db password and admin password for this work folder (created on first use)."""
    return {
        "db": _read_or_create(work / "db_password.txt", _secret),
        "admin": _read_or_create(work / "admin_password.txt", lambda: _secret() + "!A1"),  # meets OpenEMR's strength rule
    }


def _env(work: Path) -> dict:
    p = passwords(work)
    return {**os.environ, "KRISNNAI_OPENEMR_DB_PASSWORD": p["db"], "KRISNNAI_OPENEMR_ADMIN_PASSWORD": p["admin"]}


def _compose(work: Path, *args: str) -> subprocess.CompletedProcess:
    if shutil.which("docker") is None:
        raise SystemExit("Docker is not installed or not on PATH")
    return subprocess.run(["docker", "compose", "-p", PROJECT, "-f", str(COMPOSE), *args],
                          env=_env(work), check=False, text=True)  # fmt: skip


def capability(base: str = HTTPS_URL) -> httpx.Response:
    """GET the FHIR CapabilityStatement. https with the self-signed certificate: local container only."""
    return httpx.get(f"{base}{FHIR_PATH}/metadata", timeout=10, verify=False)  # noqa: S501


def up(work: Path, wait_seconds: int = 900) -> str:
    res = _compose(work, "up", "-d")
    if res.returncode != 0:
        raise SystemExit("docker compose up failed (see the output above)")
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        try:
            if capability().status_code == 200:
                return f"{HTTPS_URL}{FHIR_PATH}"
        except httpx.HTTPError:
            pass
        time.sleep(10)
    raise SystemExit(f"OpenEMR's FHIR metadata did not answer at {HTTPS_URL}{FHIR_PATH} within {wait_seconds} s "
                     f"(check: docker logs {PROJECT}-openemr-1)")  # fmt: skip


def status(work: Path) -> str:
    try:
        r = capability()
        return f"FHIR metadata HTTP {r.status_code} at {HTTPS_URL}{FHIR_PATH}"
    except httpx.HTTPError as e:
        return f"not reachable ({type(e).__name__})"


def down(work: Path) -> None:
    _compose(work, "down", "-v")
