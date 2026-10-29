# ruff: noqa: E501
"""Demo only: put synthetic payers and insurance policies into the LOCAL demo OpenEMR so the trigger has something to read.

OpenEMR's REST API cannot create a payer (it answers 500), so a payer is added with one SQL insert in the demo's own database
container; the policy itself goes in through the REST API, the way the EMR would take it. Never used against a client system.
"""

from __future__ import annotations

import subprocess
from datetime import date

from krisnnai.integrations.openemr.docker import PROJECT


def _sql(statement: str) -> str:
    res = subprocess.run(
        ["docker", "exec", f"{PROJECT}-db-1", "sh", "-c", 'mariadb -N -uroot -p"$MARIADB_ROOT_PASSWORD" openemr -e "$0"', statement],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    if res.returncode != 0:
        raise RuntimeError("could not reach the demo OpenEMR database (is the container running?)")
    return res.stdout.strip()


def ensure_payer(code: str, name: str) -> str:
    """The demo OpenEMR's id for the payer with this payer code; added if missing."""
    assert code.isalnum() and name.replace(" ", "").isalnum(), "synthetic codes only"
    got = _sql(f"select id from insurance_companies where cms_id='{code}' limit 1")
    if got:
        return got
    new = _sql("select coalesce(max(id),0)+1 from insurance_companies")
    _sql(
        "insert into insurance_companies (id,uuid,name,cms_id,ins_type_code,x12_receiver_id,x12_default_partner_id,cqm_sop) "
        f"values ({new},unhex(replace(uuid(),'-','')),'{name}','{code}',2,'{code}',1,null)"
    )
    return new


def add_policy(server, patient: dict, order: str, payer_code: str, payer_name: str, member: str, copay: str = "25", relationship: str = "self",  # noqa: ANN001
               begin: str = "2026-01-01", end: str = "2027-12-31", plan: str = "PPO") -> dict:  # fmt: skip
    """One insurance record on the patient, through the REST API. `order` is primary, secondary or tertiary."""
    body = {
        "type": order, "provider": ensure_payer(payer_code, payer_name), "plan_name": f"{payer_code} {plan}", "policy_number": member,
        "group_number": "G100", "subscriber_lname": patient["lname"], "subscriber_fname": patient["fname"],
        "subscriber_relationship": relationship, "subscriber_DOB": str(patient.get("DOB") or "1980-01-01"), "subscriber_sex": "Female",
        "subscriber_street": "100 Synthetic Way", "subscriber_city": "Testville", "subscriber_state": "TX", "subscriber_postal_code": "75001",
        "subscriber_country": "USA", "subscriber_phone": "5550100", "subscriber_employer": "", "copay": copay, "date": begin,
        "date_end": end, "accept_assignment": "TRUE",
    }  # fmt: skip
    date.fromisoformat(begin), date.fromisoformat(end)
    return server.rest_json("POST", f"/patient/{patient['uuid']}/insurance", json=body)["data"]
