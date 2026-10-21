"""Enter a charge in the local demo OpenEMR and have OpenEMR's own generator write the 837P (ADR-0002, demo only).

OpenEMR 7.0.3 has no REST endpoint for charges, so this runs a small PHP script inside OUR OpenEMR container that calls
OpenEMR's own billing code. Nothing here can reach any other system: the container name is fixed, and a write needs an
approval string saying who or what approved the codes (a named person, or a policy under ADR-0002). Synthetic data only.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

CONTAINER = "krisnai-openemr-openemr-1"
SCRIPT = Path(__file__).parent / "php" / "charge_837.php"
REMOTE = "/tmp/charge_837.php"


class BillingError(Exception):
    pass


@dataclass(frozen=True)
class Charge:
    pid: int
    encounter: int
    member: str
    payer_id: str
    payer_name: str
    dx: list[tuple[str, str]]  # (ICD-10 code, text)
    lines: list[tuple[str, str, int, str]]  # (CPT, text, units, fee as a decimal string)
    plan_name: str = "Demo PPO"


def _docker(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], input=stdin, capture_output=True, text=True, timeout=180, check=False)  # noqa: S603, S607


def charge_and_837(charge: Charge, approval: str, runner=_docker) -> dict:  # noqa: ANN001
    """{'x12': 837P text, 'log': OpenEMR's own validation notes}. `approval` is required (ADR-0002)."""
    if not approval or not approval.strip():
        raise BillingError("a charge needs an approval record: 'person:<name>' or 'policy:<id>' (ADR-0002)")
    if not charge.payer_id or not charge.lines or not charge.dx:
        raise BillingError("a charge needs a payer id, at least one diagnosis and one procedure line")
    cp = runner("cp", str(SCRIPT), f"{CONTAINER}:{REMOTE}")
    if cp.returncode:
        raise BillingError(f"the demo OpenEMR container {CONTAINER} is not reachable: {cp.stderr.strip()[:200]}")
    body = {
        "pid": charge.pid, "encounter": charge.encounter, "member": charge.member, "payer_id": charge.payer_id,
        "payer_name": charge.payer_name, "plan_name": charge.plan_name,
        "dx": [{"code": c, "text": t} for c, t in charge.dx],
        "lines": [{"cpt": c, "text": t, "units": u, "fee": f} for c, t, u, f in charge.lines],
    }  # fmt: skip
    run = runner("exec", "-i", CONTAINER, "php", REMOTE, stdin=json.dumps(body))
    if run.returncode or not run.stdout.strip():
        raise BillingError(f"the 837 step failed: {(run.stderr or run.stdout).strip()[:300]}")
    try:
        out = json.loads(run.stdout[run.stdout.index("{"):])
    except ValueError as e:
        raise BillingError(f"unexpected output from OpenEMR: {run.stdout[:200]}") from e
    if not out.get("x12", "").startswith("ISA"):
        raise BillingError(f"OpenEMR did not produce an 837: {out.get('log', '')[:200]}")
    return out
