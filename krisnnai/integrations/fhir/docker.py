"""Start and stop the local FHIR server (Microsoft FHIR server + SQL Server) with Docker Compose.

The SQL Server password is generated for this run and written under the output folder; it is a throwaway credential
for a container that only listens on 127.0.0.1. First start pulls about 2 GB of images.
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

COMPOSE = Path(__file__).with_name("docker-compose.fhir.yml")
URL = "http://localhost:8080"


def _password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "Kr1!" + "".join(secrets.choice(alphabet) for _ in range(20))  # meets SQL Server's complexity rules


def _env(work: Path) -> dict:
    pw_file = work / "sa_password.txt"
    work.mkdir(parents=True, exist_ok=True)
    if not pw_file.exists():
        pw_file.write_text(_password(), encoding="utf-8")
    return {**os.environ, "KRISNNAI_FHIR_SA_PASSWORD": pw_file.read_text(encoding="utf-8").strip()}


def _compose(work: Path, *args: str) -> subprocess.CompletedProcess:
    if shutil.which("docker") is None:
        raise SystemExit("Docker is not installed or not on PATH")
    return subprocess.run(
        ["docker", "compose", "-p", "krisnnai-fhir", "-f", str(COMPOSE), *args],
        env=_env(work), check=False, text=True,
    )


def up(work: Path, wait_seconds: int = 300) -> str:
    res = _compose(work, "up", "-d")
    if res.returncode != 0:
        raise SystemExit("docker compose up failed (see the output above)")
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        try:
            if httpx.get(f"{URL}/Patient", params={"_count": 1}, timeout=5).status_code == 200:
                return URL  # a search answering 200 means the schema is initialised and security is off
        except httpx.HTTPError:
            pass
        time.sleep(5)
    raise SystemExit(f"the FHIR server did not answer at {URL}/Patient within {wait_seconds} s")


def down(work: Path) -> None:
    _compose(work, "down", "-v")
