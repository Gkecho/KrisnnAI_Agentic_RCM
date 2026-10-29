"""Run Synthea inside Docker so nothing is installed on the host (Java 17+ is needed and is not on this PC).

The jar is downloaded once into `cache_dir`; the container is a plain JRE image. Both downloads need the user's
approval, so `plan()` returns the exact steps without running anything and `run()` only runs what `plan()` lists.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

JAR_URL = (
    "https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/"
    "synthea-with-dependencies.jar"
)
IMAGE = "eclipse-temurin:17-jre"
JAR_NAME = "synthea-with-dependencies.jar"


@dataclass(frozen=True)
class RunPlan:
    jar: Path
    out_dir: Path
    download: list[str]
    docker: list[str]


def plan(out_dir: Path, cache_dir: Path, population: int, seed: int, state: str, years: int = 2) -> RunPlan:
    jar = cache_dir / JAR_NAME
    download = ["curl", "-L", "--fail", "-o", str(jar), JAR_URL]
    docker = [
        "docker", "run", "--rm",
        "-v", f"{jar.parent.resolve()}:/jar:ro", "-v", f"{out_dir.resolve()}:/out",
        IMAGE, "java", "-jar", f"/jar/{JAR_NAME}",
        "-p", str(population), "-s", str(seed), "--exporter.baseDirectory=/out",
        "--exporter.csv.export=true", "--exporter.fhir.export=false",
        f"--exporter.years_of_history={years}", state,
    ]  # fmt: skip
    return RunPlan(jar, out_dir, download, docker)


def run(p: RunPlan) -> int:
    p.out_dir.mkdir(parents=True, exist_ok=True)
    p.jar.parent.mkdir(parents=True, exist_ok=True)
    if not p.jar.exists():
        subprocess.run(p.download, check=True)
    return subprocess.run(p.docker, check=False).returncode
